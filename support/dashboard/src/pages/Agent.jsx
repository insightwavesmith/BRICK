import { useDashboard } from '../data/useDashboard.js'
import { laneKo, toolKo, canWrite } from '../data/labels.js'

export default function Agent() {
  const d = useDashboard()
  if (!d) return <main className="container mx-auto px-6 py-12 text-black/50 font-bold">불러오는 중…</main>
  const agents = (d.agents || []).slice().sort((a, b) => b.load - a.load)
  const maxLoad = Math.max(1, ...agents.map((a) => a.load))
  const busy = agents.filter((a) => a.load > 0)

  return (
    <main className="flex-grow container mx-auto px-6 py-12">
      <div className="mb-12 border-b-2 border-black pb-4">
        <h1 className="font-headline text-5xl font-black mb-2 tracking-tight">에이전트 현황</h1>
        <p className="font-body text-lg text-zinc-600 font-medium">
          역할(레인)이지 사람 수가 아닙니다. · 총 {agents.length}개 역할 · 숫자 = <b>닫히지 않은</b> 빌딩에서 현재 위치한 브릭 수(마감 대기·멈춤 포함, 실시간 실행 아님)
        </p>
      </div>

      <section className="mb-16">
        <h2 className="font-headline text-3xl font-bold mb-8 flex items-center">
          <span className="material-symbols-outlined mr-3 text-4xl">group</span>보유 현황
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {agents.map((a) => {
            const on = a.load > 0
            return (
              <div key={a.id} className={`border-4 bg-white p-6 relative flex flex-col hover:-translate-y-1 transition-transform duration-200 ${on ? 'border-black' : 'border-black/25'}`}>
                <div className={`absolute top-0 right-0 px-3 py-1 font-bold text-sm ${on ? 'bg-black text-white' : 'bg-black/15 text-black/50'}`}>{laneKo(a.lane)}</div>
                <h3 className="font-headline text-2xl font-black mb-4 mt-2">{a.id}</h3>
                <div className="mb-4 flex flex-wrap gap-2">
                  <span className="inline-block border-2 border-black px-2 py-1 text-xs font-bold">레인: {laneKo(a.lane)}</span>
                  {canWrite(a.tool) && <span className="inline-block border-2 border-[#C8153C] text-[#C8153C] px-2 py-1 text-xs font-black">쓰기 가능</span>}
                </div>
                <div className="mb-4 flex-grow">
                  <p className="font-bold text-sm mb-1 border-b border-zinc-300 pb-1">스킬</p>
                  <ul className="text-sm list-disc list-inside text-zinc-700">
                    {a.skills.map((s) => <li key={s} className="font-mono text-[13px]">{s}</li>)}
                  </ul>
                </div>
                <div className="mb-4">
                  <p className="font-bold text-sm mb-1 border-b border-zinc-300 pb-1">도구정책</p>
                  <p className="text-sm text-zinc-700">{toolKo(a.tool)} · <span className="font-mono text-xs">{a.tool || '—'}</span></p>
                </div>
                <div className="border-t-2 border-black pt-4 mt-auto flex justify-between items-end">
                  <span className="font-bold text-sm">현재 맡은 브릭</span>
                  <span className={`font-headline text-4xl font-black ${on ? 'text-crimson' : 'text-black/25'}`}>{a.load}</span>
                </div>
              </div>
            )
          })}
        </div>
      </section>

      <section>
        <h2 className="font-headline text-3xl font-bold mb-8 flex items-center">
          <span className="material-symbols-outlined mr-3 text-4xl">warning</span>운영 부하 및 병목
        </h2>
        <p className="text-sm text-zinc-500 font-medium mb-6">닫히지 않은 빌딩(진행·마감대기·멈춤)에서 현재 위치한 브릭 수 기준. 막대는 가장 많은 역할({agents[0]?.id})에 대한 상대값이며, 실시간 실행량이 아니라 누적 미마감 분포입니다.</p>
        <div className="space-y-4">
          {busy.map((a, i) => {
            const top = i === 0
            return (
              <div key={a.id} className="border-2 border-black bg-white p-6">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-4">
                  <div className="flex items-center mb-2 md:mb-0">
                    <h3 className="font-headline text-2xl font-black mr-4">{a.id}</h3>
                    {top && (
                      <span className="bg-crimson text-white px-3 py-1 text-xs font-bold uppercase tracking-wider flex items-center">
                        <span className="material-symbols-outlined text-sm mr-1">priority_high</span> 최다 부하 (병목)
                      </span>
                    )}
                  </div>
                  <div className={`font-bold text-lg ${top ? 'text-crimson' : 'text-zinc-700'}`}>{a.load}개 브릭</div>
                </div>
                <div className="w-full h-6 border-2 border-black bg-zinc-100 flex relative overflow-hidden">
                  <div className={`h-full ${top ? 'bg-crimson' : 'bg-black'} transition-all duration-700`} style={{ width: `${Math.round((a.load / maxLoad) * 100)}%` }}></div>
                </div>
              </div>
            )
          })}
          {busy.length === 0 && <div className="border-2 border-black/20 p-6 text-black/40 font-bold">현재 진행 중인 브릭이 없습니다.</div>}
        </div>
      </section>
    </main>
  )
}
