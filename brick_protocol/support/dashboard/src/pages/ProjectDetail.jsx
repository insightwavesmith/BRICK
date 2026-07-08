import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useDashboard } from '../data/useDashboard.js'
import { BRICK, brickKo } from '../data/labels.js'

function phaseKo(ref) {
  if (!ref) return null
  const keys = Object.keys(BRICK).sort((a, b) => b.length - a.length)
  for (const k of keys) if (ref.endsWith(k)) return brickKo(k)
  return null
}

function Row({ b }) {
  const ph = phaseKo(b.currentBrick)
  return (
    <Link to={`/building/${encodeURIComponent(b.key || b.id)}`}
      className="bg-white border-2 border-black p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:shadow-[4px_4px_0_#000] transition-shadow">
      <div className="min-w-0 flex-1">
        <div className="font-bold text-base truncate">{b.id}</div>
        <div className="text-xs text-gray-600 font-label">
          {ph ? `단계: ${ph}` : '단계 미상'}{b.missing > 0 ? ` · 누락 ${b.missing}` : ''}{b.ageDays != null ? ` · ${b.ageDays}일 전 증거` : ''}
        </div>
      </div>
      <div className="flex items-center gap-2 text-sm font-label font-bold shrink-0">
        {b.stale && <span className="bg-yellow-100 text-yellow-700 border border-yellow-500 px-2 py-0.5 text-xs">오래됨</span>}
        {b.currentAgent && <span className="bg-gray-200 px-2 py-1 border border-black">{b.currentAgent}</span>}
        <span className="material-symbols-outlined text-black/40 text-lg">chevron_right</span>
      </div>
    </Link>
  )
}

function Group({ title, icon, items, tone, empty }) {
  const has = items.length > 0
  const toneCls = !has ? 'bg-gray-50 border-l-black/30' :
    tone === 'red' ? 'bg-red-50 border-l-[#C8153C]' :
    tone === 'amber' ? 'bg-yellow-50 border-l-yellow-500' : 'bg-white border-l-black'
  const txtCls = !has ? 'text-black/40' : tone === 'red' ? 'text-[#C8153C]' : tone === 'amber' ? 'text-yellow-700' : 'text-black'
  return (
    <div className={`border-l-4 border-y-2 border-r-2 border-black p-4 ${toneCls}`}>
      <h3 className={`font-bold font-label text-sm uppercase tracking-wider mb-4 flex items-center gap-2 ${txtCls}`}>
        <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>{icon}</span>
        {title} ({items.length})
      </h3>
      {has ? <div className="space-y-2">{items.map((b) => <Row key={b.key || b.id} b={b} />)}</div>
        : <p className="text-sm text-black/40 font-medium">{empty}</p>}
    </div>
  )
}

export default function ProjectDetail() {
  const { id } = useParams()
  const d = useDashboard()
  const [showDone, setShowDone] = useState(false)
  const [showPending, setShowPending] = useState(false)
  const [showArchived, setShowArchived] = useState(false)
  if (!d) return <div className="max-w-7xl mx-auto px-4 py-8 text-black/50 font-bold">불러오는 중…</div>
  const p = d.projects.find((x) => x.id === id) || d.projects[0]
  const c = (p && p.counts) || {}
  const all = d.buildings.filter((b) => b.project === (p?.id))
  const G = (k) => all.filter((b) => b.disp === k)
  const running = G('running'), pending = G('closure_pending'), stopped = G('stopped')
  const review = G('review'), incomplete = G('incomplete'), done = G('closed')
  const archived = G('archived_stale')
  const attn = stopped.length + review.length
  const pendingShown = showPending ? pending : pending.slice(0, 8)
  const archivedShown = showArchived ? archived : archived.slice(0, 6)

  const KPI = ({ l, v, tone }) => (
    <div className={`p-6 border-[3px] shadow-[4px_4px_0px_0px_black] ${
      tone === 'black' ? 'bg-black text-white border-black' :
      v > 0 && tone === 'red' ? 'bg-red-50 text-[#C8153C] border-[#C8153C]' :
      v > 0 && tone === 'amber' ? 'bg-yellow-50 text-yellow-700 border-yellow-500' :
      tone === 'gray' ? 'bg-gray-100 text-black border-black' : 'bg-white text-black/30 border-black/20'}`}>
      <div className="font-label text-sm font-bold uppercase tracking-wider mb-2">{l}</div>
      <div className="text-4xl font-black font-display">{v}</div>
    </div>
  )

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <nav className="flex text-sm font-label font-bold mb-2">
            <ol className="flex items-center space-x-2">
              <li><Link className="text-gray-500 hover:text-black transition-colors" to="/">프로젝트</Link></li>
              <li><span className="text-gray-400 mx-2">/</span></li>
              <li className="text-[#C8153C] uppercase tracking-wider">{p?.label || p?.id}</li>
            </ol>
          </nav>
          <h1 className="text-3xl md:text-4xl font-black font-display tracking-tight">{p?.label || p?.id}</h1>
        </div>
        <div className="inline-flex items-center gap-2 bg-gray-100 px-4 py-2 border-2 border-black font-label text-sm font-bold">
          <span className="material-symbols-outlined text-gray-500 text-sm">schedule</span>
          <span>스냅샷: {d.generatedAt || '—'}</span>
          <span className="text-gray-500">| 라이브 재생성</span>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-12">
        <KPI l="전체" v={p?.total || 0} tone="black" />
        <KPI l="완료" v={c.closed || 0} tone="gray" />
        <KPI l="진행 중" v={c.running || 0} tone="red" />
        <KPI l="마감 대기" v={c.closure_pending || 0} tone="amber" />
        <KPI l="멈춤·검수" v={attn} tone="red" />
        <KPI l="데이터 미완" v={c.incomplete || 0} tone="red" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-12">
          <section>
            <h2 className="text-2xl font-black font-display tracking-tight border-b-4 border-black pb-2 mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined text-[#C8153C]">priority_high</span>손이 필요한 것
            </h2>
            <div className="space-y-6">
              <Group title="진행 중" icon="play_circle" items={running} tone="plain" empty="실제 작업 진행 중인 빌딩이 없습니다." />
              <Group title="멈춤" icon="error" items={stopped} tone="red" empty="멈춘 빌딩이 없습니다." />
              <Group title="검수 대기" icon="how_to_reg" items={review} tone="amber" empty="검수 대기가 없습니다." />
              <Group title="데이터 미완" icon="warning" items={incomplete} tone="amber" empty="없음." />
            </div>
          </section>

          {pending.length > 0 && (
            <section>
              <h2 className="text-2xl font-black font-display tracking-tight border-b-4 border-yellow-500 pb-2 mb-6 flex items-center gap-2 text-yellow-700">
                <span className="material-symbols-outlined">schedule</span>마감 대기 ({pending.length})
              </h2>
              <p className="text-sm text-gray-600 font-medium mb-4">
                마지막 브릭까지 갔으나 마감 도장이 안 찍힌 빌딩(최근 {d.staleDays}일 이내 증거). 실행 중이 아니라 끝맺지 않은 상태입니다.
              </p>
              <div className="space-y-2">
                {pendingShown.map((b) => <Row key={b.key || b.id} b={b} />)}
              </div>
              {pending.length > 8 && (
                <button onClick={() => setShowPending(!showPending)} className="mt-4 text-sm font-black underline">
                  {showPending ? '접기 ▴' : `전체 ${pending.length}개 보기 ▾`}
                </button>
              )}
            </section>
          )}

          {archived.length > 0 && (
            <section>
              <h2 className="text-2xl font-black font-display tracking-tight border-b-4 border-gray-300 pb-2 mb-6 flex items-center gap-2 text-gray-500">
                <span className="material-symbols-outlined">inventory_2</span>오래된 미마감 · 접어둠 ({archived.length})
              </h2>
              <p className="text-sm text-gray-500 font-medium mb-4">
                마지막 증거가 {d.staleDays}일 넘게 지난 미마감 잔재. <b>완료가 아니며</b> 살아있는 카운트에서 빼서 접어뒀습니다.
                실제로 끝났다면 엔진에서 마감하면 자동으로 완료로 바뀝니다(화면은 거울이라 손대지 않습니다).
              </p>
              <div className="space-y-2 opacity-75">
                {archivedShown.map((b) => <Row key={b.key || b.id} b={b} />)}
              </div>
              {archived.length > 6 && (
                <button onClick={() => setShowArchived(!showArchived)} className="mt-4 text-sm font-black underline">
                  {showArchived ? '접기 ▴' : `전체 ${archived.length}개 보기 ▾`}
                </button>
              )}
            </section>
          )}

          <section>
            <h2 className="text-2xl font-black font-display tracking-tight border-b-4 border-black pb-2 mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined">task_alt</span>완료 ({done.length})
            </h2>
            <div className="bg-gray-50 border-2 border-black p-4">
              <div className="flex flex-wrap gap-2">
                {(showDone ? done : done.slice(0, 12)).map((b) => (
                  <Link key={b.key || b.id} to={`/building/${encodeURIComponent(b.key || b.id)}`}
                    className="text-xs font-bold bg-white border border-black px-2 py-1 hover:bg-black hover:text-white transition-colors truncate max-w-[220px]">
                    {b.id}
                  </Link>
                ))}
              </div>
              {done.length > 12 && (
                <button onClick={() => setShowDone(!showDone)} className="mt-4 text-sm font-black underline">
                  {showDone ? '접기 ▴' : `전체 ${done.length}개 보기 ▾`}
                </button>
              )}
            </div>
          </section>
        </div>

        <div className="lg:col-span-1">
          <aside className="sticky top-24">
            <h2 className="text-2xl font-black font-display tracking-tight border-b-4 border-[#C8153C] pb-2 mb-6 flex items-center gap-2 text-[#C8153C]">
              <span className="material-symbols-outlined text-[#C8153C]">donut_large</span>구성
            </h2>
            <div className="bg-white border-4 border-black p-6 shadow-[4px_4px_0px_0px_black] space-y-5">
              <div className="text-sm font-label font-bold text-gray-500 uppercase tracking-wider">스냅샷 구성 · 추세(시계열) 데이터 없음</div>
              {[
                { l: '완료', v: c.closed || 0, cls: 'bg-black' },
                { l: '오래된 미마감(접어둠)', v: c.archived_stale || 0, cls: 'bg-gray-400' },
                { l: '마감 대기', v: c.closure_pending || 0, cls: 'bg-yellow-500' },
                { l: '진행 중', v: c.running || 0, cls: 'bg-[#C8153C]' },
                { l: '멈춤·검수', v: attn, cls: 'bg-[#C8153C]' },
                { l: '데이터 미완', v: c.incomplete || 0, cls: 'bg-gray-400' },
              ].map((s) => (
                <div key={s.l}>
                  <div className="flex justify-between items-baseline mb-1">
                    <span className="font-bold">{s.l}</span>
                    <span className="text-xl font-black font-display">{s.v}</span>
                  </div>
                  <div className="w-full h-2 bg-gray-100 border border-black">
                    <div className={`h-full ${s.cls}`} style={{ width: `${p?.total ? Math.round((s.v / p.total) * 100) : 0}%` }}></div>
                  </div>
                </div>
              ))}
              <div className="pt-4 mt-2 border-t-2 border-black flex items-start gap-3 bg-gray-50 p-3">
                <span className="material-symbols-outlined text-[#C8153C]">info</span>
                <p className="text-sm font-body text-gray-700 leading-relaxed">
                  읽기 전용 스냅샷입니다. 진행률·ETA·추세는 이 데이터에 없어 표시하지 않습니다.
                </p>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  )
}
