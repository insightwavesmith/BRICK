// 실시간 대시보드 서버 (Cloud Run 용). 의존성 0 (순수 Node http).
//   1) 빌드된 React 정적 앱(dist/) 서빙
//   2) POST /ingest  — 발행 측이 seed/delta(또는 legacy full) 밀어넣음 (공유 시크릿 인증)
//   3) GET  /events  — SSE. 연결 즉시 참가자별 seed + 이후 seed/delta 푸시
// 참가자별로 보관(다인용). 빌딩 델타는 그 참가자 packet 의 buildings 만 교체(집계는 클라가 재계산).
// 원본은 repo ledger / Building evidence. 이 서버는 받아서 비추는 projection일 뿐.
import http from 'node:http'
import { createHmac, timingSafeEqual } from 'node:crypto'
import { stat, readFile } from 'node:fs/promises'
import { createReadStream } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const PORT = process.env.PORT || 8080
const RAW_INGEST_SECRET = process.env.INGEST_SECRET
const NORMALIZED_INGEST_SECRET = RAW_INGEST_SECRET && RAW_INGEST_SECRET.trim()
const INGEST_SECRET = NORMALIZED_INGEST_SECRET || 'dev-secret'
const IS_PRODUCTION = process.env.NODE_ENV === 'production'
const DIST = process.env.DIST_DIR || path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'dist')

const participants = {} // ref -> { ref, label, packet }
const clients = new Set()
const seenEventIds = new Set()
const seenEventOrder = []
const participantSequences = new Map()
const INGEST_TIMESTAMP_SKEW_SECONDS = 5 * 60
const INGEST_REPLAY_CACHE_LIMIT = 4096

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon',
  '.woff2': 'font/woff2', '.woff': 'font/woff', '.map': 'application/json',
}

// SSE: payload 가 여러 줄이어도 각 줄 data: 접두 → 브라우저가 \n 으로 복원
function sseFrame(event, jsonStr) {
  return `event: ${event}\n` + jsonStr.split('\n').map((l) => 'data: ' + l).join('\n') + '\n\n'
}
function broadcast(event, jsonStr) {
  const frame = sseFrame(event, jsonStr)
  for (const res of clients) { try { res.write(frame) } catch { /* 끊김 무시 */ } }
}

function ingestRefusesInProduction() {
  return IS_PRODUCTION && (!NORMALIZED_INGEST_SECRET || NORMALIZED_INGEST_SECRET === 'dev-secret')
}

function rememberEventId(eventId) {
  seenEventIds.add(eventId)
  seenEventOrder.push(eventId)
  while (seenEventOrder.length > INGEST_REPLAY_CACHE_LIMIT) {
    seenEventIds.delete(seenEventOrder.shift())
  }
}

function headerValue(req, name) {
  const value = req.headers[name]
  return Array.isArray(value) ? value[0] : value
}

function safeEqualText(a, b) {
  const left = Buffer.from(a || '', 'utf8')
  const right = Buffer.from(b || '', 'utf8')
  return left.length === right.length && timingSafeEqual(left, right)
}

function expectedIngestSignature({ body, eventId, timestamp }) {
  const base = `${timestamp}.${eventId}.`
  return 'sha256=' + createHmac('sha256', INGEST_SECRET).update(base).update(body, 'utf8').digest('hex')
}

function verifyIngestSignature(req, body) {
  if (headerValue(req, 'x-ingest-secret') !== INGEST_SECRET) return { ok: false, status: 401, reason: 'unauthorized' }
  const timestamp = headerValue(req, 'x-ingest-timestamp')
  const eventId = headerValue(req, 'x-ingest-event-id')
  const signature = headerValue(req, 'x-ingest-signature')
  if (!timestamp || !eventId || !signature) return { ok: false, status: 401, reason: 'missing ingest signature' }
  if (seenEventIds.has(eventId)) return { ok: false, status: 409, reason: 'replayed ingest event' }
  const timestampNumber = Number(timestamp)
  if (!Number.isInteger(timestampNumber)) return { ok: false, status: 401, reason: 'bad ingest timestamp' }
  const now = Math.floor(Date.now() / 1000)
  if (Math.abs(now - timestampNumber) > INGEST_TIMESTAMP_SKEW_SECONDS) {
    return { ok: false, status: 401, reason: 'stale ingest timestamp' }
  }
  const expected = expectedIngestSignature({ body, eventId, timestamp })
  if (!safeEqualText(signature, expected)) return { ok: false, status: 401, reason: 'bad ingest signature' }
  return { ok: true, eventId }
}

function messageSequence(msg) {
  const sequence = msg && msg.sequence
  return Number.isInteger(sequence) && sequence > 0 ? sequence : null
}

function rejectSequenceRollback(ref, msg) {
  const sequence = messageSequence(msg)
  if (sequence === null) return 'missing ingest sequence'
  const previous = participantSequences.get(ref) || 0
  if (sequence <= previous) return 'ingest sequence rollback'
  participantSequences.set(ref, sequence)
  return ''
}

// 빌딩 델타 1건을 packet 에 병합 (집계는 안 건드림 — 클라가 재계산)
// 키 = (project, building_id) 복합: 같은 building_id 가 두 동네에 있어도 서로 못 덮는다.
// 레거시(델타에 building_key 없음 / 행에 key 없음)는 building_id 단독 키로 동작 유지.
function buildingKeyOf(b) {
  if (!b) return ''
  return b.key || (b.project ? b.project + '/' + b.id : b.id)
}
function applyDelta(packet, delta) {
  const base = packet || { buildings: [], detail: {} }
  const deltaKey = delta.building_key || delta.building_id
  // 레거시 델타(building_key 없음)는 레거시 행(key/project 없는 행)만 지운다 —
  // 프로젝트 키가 붙은 행을 id 단독으로 지우면 동네 간 클로버(S5-FIX: 같은 id가
  // 두 동네에 있을 때 레거시 델타 하나가 전 동네 행을 갈아치웠다).
  const hits = delta.building_key
    ? (b) => buildingKeyOf(b) === deltaKey
    : (b) => !(b.key || b.project) && b.id === delta.building_id
  const buildings = (base.buildings || []).filter((b) => !hits(b))
  if (!delta.removed && delta.building) buildings.push(delta.building)
  const detail = { ...(base.detail || {}) }
  if (delta.removed) delete detail[deltaKey]
  else if (delta.detail) detail[deltaKey] = delta.detail
  return { ...base, buildings, detail, generatedAt: delta.generatedAt || base.generatedAt }
}

function seedMessage(p) {
  return JSON.stringify({ kind: 'seed', participant_ref: p.ref, participant_label: p.label, packet: p.packet })
}

async function readBody(req, limit = 16 * 1024 * 1024) {
  const chunks = []
  let size = 0
  for await (const c of req) {
    size += c.length
    if (size > limit) throw new Error('payload too large')
    chunks.push(c)
  }
  return Buffer.concat(chunks).toString('utf8')
}

async function serveStatic(req, res, urlPath) {
  let rel = decodeURIComponent(urlPath.split('?')[0])
  if (rel === '/' || rel === '') rel = '/index.html'
  let file = path.join(DIST, rel)
  if (!file.startsWith(DIST)) { res.writeHead(403).end('forbidden'); return }
  try {
    const s = await stat(file)
    if (s.isDirectory()) file = path.join(file, 'index.html')
  } catch {
    file = path.join(DIST, 'index.html') // SPA 폴백
  }
  try {
    res.writeHead(200, { 'content-type': MIME[path.extname(file)] || 'application/octet-stream' })
    createReadStream(file).pipe(res)
  } catch {
    res.writeHead(404).end('not found')
  }
}

const server = http.createServer(async (req, res) => {
  const url = req.url || '/'

  if (url === '/healthz') { res.writeHead(200).end('ok'); return }

  // 발행 측 → seed / delta / legacy-full 수신
  if (url === '/ingest' && req.method === 'POST') {
    if (ingestRefusesInProduction()) {
      res.writeHead(503).end('ingest disabled: set INGEST_SECRET')
      return
    }
    try {
      const body = await readBody(req)
      const signatureCheck = verifyIngestSignature(req, body)
      if (!signatureCheck.ok) { res.writeHead(signatureCheck.status).end(signatureCheck.reason); return }
      const msg = JSON.parse(body)
      if (!msg || msg.event_id !== signatureCheck.eventId) { res.writeHead(401).end('ingest event id mismatch'); return }
      let kind = 'data'
      // 발행(엔진 report_sinks) 계약: 델타 = delta_kind:"building", 시드 = bare 전체 패킷.
      // (kind:"delta"/"seed" 래퍼도 계속 인식 — 수신은 둘 다 받는다.)
      if (msg && msg.delta_kind === 'building') msg.kind = 'delta'
      if (msg && msg.kind === 'delta') {
        const ref = msg.participant_ref || 'default'
        const sequenceError = rejectSequenceRollback(ref, msg)
        if (sequenceError) { res.writeHead(409).end(sequenceError); return }
        rememberEventId(signatureCheck.eventId)
        if (participants[ref]) participants[ref].packet = applyDelta(participants[ref].packet, msg)
        broadcast('delta', body); kind = 'delta'
      } else if (msg && msg.kind === 'seed') {
        const ref = msg.participant_ref || 'default'
        const sequenceError = rejectSequenceRollback(ref, msg)
        if (sequenceError) { res.writeHead(409).end(sequenceError); return }
        rememberEventId(signatureCheck.eventId)
        participants[ref] = { ref, label: msg.participant_label || '나', packet: msg.packet }
        broadcast('seed', body); kind = 'seed'
      } else {
        // bare packet (정적/legacy) → 단일 기본 참가자
        const sequenceError = rejectSequenceRollback('default', msg)
        if (sequenceError) { res.writeHead(409).end(sequenceError); return }
        rememberEventId(signatureCheck.eventId)
        participants.default = { ref: 'default', label: (msg && msg.participant_label) || '나', packet: msg }
        broadcast('data', body); kind = 'data'
      }
      res.writeHead(200, { 'content-type': 'application/json' })
        .end(JSON.stringify({ ok: true, kind, participants: Object.keys(participants).length, clients: clients.size }))
    } catch (e) {
      res.writeHead(400).end('bad json: ' + e.message)
    }
    return
  }

  // 브라우저 → SSE 구독: 연결 시 참가자별 seed 1회, 이후 push
  if (url === '/events') {
    res.writeHead(200, {
      'content-type': 'text/event-stream',
      'cache-control': 'no-cache, no-transform',
      connection: 'keep-alive',
      'x-accel-buffering': 'no',
    })
    res.write('retry: 3000\n\n')
    for (const p of Object.values(participants)) res.write(sseFrame('seed', seedMessage(p)))
    clients.add(res)
    const ping = setInterval(() => { try { res.write(': ping\n\n') } catch {} }, 25000)
    req.on('close', () => { clearInterval(ping); clients.delete(res) })
    return
  }

  // 폴백 데이터 (SSE 못 쓰는 첫 로드용): 기본 참가자 packet, 없으면 빌드 동봉 스냅샷
  if (url.split('?')[0] === '/dashboard-data.json') {
    const p = participants.default || Object.values(participants)[0]
    if (p) { res.writeHead(200, { 'content-type': 'application/json' }).end(JSON.stringify(p.packet)); return }
    return serveStatic(req, res, '/dashboard-data.json')
  }

  if (req.method === 'GET') return serveStatic(req, res, url)
  res.writeHead(405).end('method not allowed')
})

// 부팅 시 빌드 동봉 스냅샷을 기본 참가자로 → 콜드스타트(메모리 비어도)에도 데이터가 뜬다.
try {
  const baked = await readFile(path.join(DIST, 'dashboard-data.json'), 'utf8')
  participants.default = { ref: 'default', label: '나', packet: JSON.parse(baked) }
  console.log('[surface-server] baked snapshot loaded as default participant')
} catch {
  console.log('[surface-server] no baked snapshot (empty until ingest)')
}

server.listen(PORT, () => {
  const ingestMode = ingestRefusesInProduction() ? 'disabled' : INGEST_SECRET === 'dev-secret' ? 'dev' : 'configured'
  console.log(`[surface-server] :${PORT} (ingest ${ingestMode})`)
})
