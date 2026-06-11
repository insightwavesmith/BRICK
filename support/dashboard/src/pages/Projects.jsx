import { Link } from 'react-router-dom'
import { useDashboard } from '../data/useDashboard.js'

const Stat = ({ l, v, sub, red, amber }) => (
  <div className="flex flex-col items-center flex-1 w-full">
    <span className="text-gray-500 font-label font-bold text-sm mb-1 text-center">{l}</span>
    <span className={`font-headline font-black text-4xl ${red && v > 0 ? 'status-crimson' : amber && v > 0 ? 'text-yellow-600' : ''}`}>{v}</span>
    {sub ? <span className="text-[11px] text-gray-400 font-bold mt-0.5">{sub}</span> : null}
  </div>
)
const C = ({ l, v, red, amber }) => (
  <div className="flex flex-col">
    <span className="text-gray-500 text-xs font-bold">{l}</span>
    <span className={`font-headline font-black text-xl ${red && v > 0 ? 'status-crimson' : amber && v > 0 ? 'text-yellow-600' : ''}`}>{v}</span>
  </div>
)

export default function Projects() {
  const d = useDashboard()
  if (!d) return <div className="text-black/50 font-bold py-10">불러오는 중…</div>
  const bd = d.summary.byDisplay || {}
  const attn = (bd.stopped || 0) + (bd.review || 0) // 사람 손 필요
  return (
    <div className="flex flex-col gap-8">
      <section className="bg-white block-border p-6 flex flex-col md:flex-row justify-between items-center gap-6">
        <Stat l="전체 빌딩" v={d.summary.buildings} />
        <Stat l="완료" v={bd.closed || 0} />
        <Stat l="진행 중" v={bd.running || 0} />
        <Stat l="마감 대기" v={bd.closure_pending || 0} amber />
        <Stat l="멈춤·검수" v={attn} red />
        <Stat l="데이터 미완" v={bd.incomplete || 0} red />
      </section>

      {(bd.archived_stale || 0) > 0 && (
        <div className="bg-gray-50 border-2 border-gray-300 border-l-4 border-l-gray-400 p-4 flex items-start gap-3">
          <span className="material-symbols-outlined text-gray-500">inventory_2</span>
          <p className="text-sm font-bold text-gray-600 leading-relaxed">
            오래된 미마감 <b className="text-gray-800">{bd.archived_stale}</b>개 — 마지막 증거가 {d.staleDays}일 넘게 지나 <b>살아있는 카운트에서 접어뒀습니다</b>.
            실행 중이 아니라 마감 도장만 안 찍힌 잔재이며, <b>완료가 아닙니다</b>. 처리는 거울(화면)이 아니라 엔진에서 실제 마감해야 반영됩니다.
          </p>
        </div>
      )}

      <section className="flex flex-col gap-6">
        <div className="flex items-end justify-between">
          <h2 className="font-headline font-black text-2xl">활성 프로젝트</h2>
          <span className="text-xs text-gray-500 font-bold">라이브 재생성 · {d.generatedAt?.slice(0, 10)}</span>
        </div>
        <div className="flex flex-col gap-4">
          {d.projects.map((p) => {
            const c = p.counts || {}
            const at = (c.stopped || 0) + (c.review || 0)
            return (
              <Link key={p.id} to={`/project/${encodeURIComponent(p.id)}`}
                className={`bg-white block-border p-6 flex flex-col gap-4 hover:shadow-[6px_6px_0_#000] transition-shadow ${at > 0 ? 'border-l-[6px] border-l-[#C8153C]' : ''}`}>
                <div className="flex justify-between items-start">
                  <h3 className="font-headline font-black text-2xl">{p.label || p.id}</h3>
                  <span className="bg-black text-white px-3 py-1 font-bold text-sm block-border">빌딩 {p.total}</span>
                </div>
                <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
                  <C l="완료" v={c.closed || 0} />
                  <C l="진행" v={c.running || 0} />
                  <C l="마감 대기" v={c.closure_pending || 0} amber />
                  <C l="멈춤·검수" v={at} red />
                  <C l="데이터 미완" v={c.incomplete || 0} red />
                  <C l="오래된 미마감" v={c.archived_stale || 0} />
                </div>
              </Link>
            )
          })}
        </div>
      </section>
    </div>
  )
}
