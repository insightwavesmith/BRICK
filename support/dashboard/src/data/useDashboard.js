import { useEffect, useReducer } from 'react'
import { recompute, applyDelta } from './aggregate.js'

// 참가자별 원본 상태 보관 (다인용). 화면은 "선택된 참가자"의 packet 을 집계 재계산해서 받는다.
// 수신 메시지 3종:
//   - bare packet (정적/baked, kind 없음)         → 단일 기본 참가자 seed
//   - { kind:'seed', participant_ref, packet }    → 그 참가자 전체 교체
//   - { kind:'delta', participant_ref, building }  → 그 참가자 빌딩 1개 갱신
const participants = {} // ref -> { ref, label, packet }
let selectedRef = null
let started = false
const listeners = new Set()
const notify = () => listeners.forEach((l) => l())

function seed(ref, label, packet) {
  participants[ref] = { ref, label: label || (participants[ref] && participants[ref].label) || '나', packet }
  if (!selectedRef || !participants[selectedRef]) selectedRef = ref
}

function handle(msg) {
  if (!msg) return
  // 발행(엔진 report_sinks) 계약: 델타 = delta_kind:"building" (kind 래퍼도 계속 인식)
  if (msg.delta_kind === 'building') msg = { ...msg, kind: 'delta' }
  if (msg.kind === 'delta') {
    const ref = msg.participant_ref || 'default'
    const p = participants[ref]
    if (p) p.packet = applyDelta(p.packet, msg) // seed 먼저 와야 함; 없으면 무시(다음 seed가 교정)
  } else if (msg.kind === 'seed') {
    seed(msg.participant_ref || 'default', msg.participant_label, msg.packet)
  } else {
    seed('default', msg.participant_label || '나', msg) // bare packet (정적/baked)
  }
  notify()
}

function fallbackFetch() {
  fetch('/dashboard-data.json', { cache: 'no-store' }).then((r) => r.json()).then(handle).catch(() => {})
}

function start() {
  if (started) return
  started = true
  if (typeof EventSource !== 'undefined') {
    try {
      const es = new EventSource('/events')
      const onMsg = (e) => { try { handle(JSON.parse(e.data)) } catch { /* skip */ } }
      es.addEventListener('data', onMsg) // 기존 full 호환
      es.addEventListener('seed', onMsg)
      es.addEventListener('delta', onMsg)
      // SSE 연결 실패(예: vite dev엔 /events 없음)일 때만 fetch 폴백 → 중복 default 방지
      es.onerror = () => { if (!Object.keys(participants).length) fallbackFetch() }
      return
    } catch { /* SSE 불가 → 폴백 */ }
  }
  fallbackFetch()
}

// 선택된 참가자의 화면 데이터 (집계 재계산). 페이지들은 기존처럼 그대로 사용.
export function useDashboard() {
  const [, force] = useReducer((x) => x + 1, 0)
  useEffect(() => { listeners.add(force); start(); return () => listeners.delete(force) }, [])
  const p = selectedRef ? participants[selectedRef] : null
  return p ? recompute(p.packet) : null
}

// 팀원 선택 셀렉터용
export function useParticipants() {
  const [, force] = useReducer((x) => x + 1, 0)
  useEffect(() => { listeners.add(force); start(); return () => listeners.delete(force) }, [])
  return {
    participants: Object.values(participants).map((x) => ({ ref: x.ref, label: x.label })),
    selectedRef,
    setSelected: (ref) => { if (participants[ref]) { selectedRef = ref; notify() } },
  }
}
