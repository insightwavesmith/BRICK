import { useDashboard } from '../data/useDashboard.js'
import { movementKo, ownerKo } from '../data/labels.js'

export default function LinkPage() {
  const d = useDashboard()
  if (!d) return <main className="max-w-7xl mx-auto px-6 py-12 text-black/50 font-bold">불러오는 중…</main>
  const mv = d.links?.movement || {}
  const forwardCount = mv.forward || 0
  const rerouteCount = (mv.reroute || 0) + (mv.return || 0)
  const lifecycleStopCount = mv.stop || 0
  const fan = d.links?.fan || {}
  const disp = d.links?.dispositions || {}
  const dispEntries = Object.entries(disp)
  const dispTotal = dispEntries.reduce((s, [, v]) => s + v, 0)

  return (
    <main className="max-w-7xl mx-auto px-6 py-12">
      <header className="mb-12 border-b-4 border-black pb-8">
        <h1 className="font-headline font-black text-5xl md:text-6xl tracking-tighter text-black mb-4">링크 · 게이트 현황</h1>
        <p className="font-body text-xl text-gray-700 max-w-3xl">
          브릭과 브릭 사이의 넘김(링크)을 제어하는 게이트 규칙과, 전체 {d.summary?.buildings ?? 0}개 빌딩에서의 실제 적용 집계입니다.
          <span className="text-gray-500"> · 스냅샷 · 규칙 설정은 차후 지원</span>
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* 충분성 */}
        <div className="border-4 border-black p-6 bg-white hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] transition-shadow duration-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-3 mb-4">
              <span className="material-symbols-outlined text-3xl text-black">fact_check</span>
              <h2 className="font-headline font-extrabold text-2xl tracking-tight">게이트 충분성</h2>
            </div>
            <div className="space-y-4 font-body">
              <p className="text-gray-700">다음 브릭으로 넘기기 전, 필요한 공개 사실이 모였는지 관찰합니다. 부족하면 전진하지 않고 보류 상태로 남습니다.</p>
              <div className="p-4 bg-gray-50 border-2 border-black border-dashed text-sm">
                <span className="font-bold block mb-1">집계 위치</span>
                이 스냅샷에는 GateFact 단독 카운터가 없고, 보류는 빌딩 상태 집계에서 봅니다.
              </div>
            </div>
          </div>
          <div className="mt-6 pt-6 border-t-2 border-black flex justify-between items-end">
            <div className="font-headline font-bold">
              <span className="text-gray-600 block text-sm">수명주기 멈춤 표기</span>
              <span className="text-3xl text-crimson">{lifecycleStopCount}<span className="text-lg">건</span></span>
            </div>
            <p className="text-gray-400 text-xs font-medium uppercase tracking-wider text-right self-end">설정 · 차후 지원</p>
          </div>
        </div>

        {/* 움직임 */}
        <div className="border-4 border-black p-6 bg-white hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] transition-shadow duration-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-3 mb-4">
              <span className="material-symbols-outlined text-3xl text-black">arrow_forward</span>
              <h2 className="font-headline font-extrabold text-2xl tracking-tight">링크 이동</h2>
            </div>
            <div className="space-y-4 font-body">
              <p className="text-gray-700">각 빌딩의 가장 최근 Link Movement 관찰값입니다. active literal은 전진과 재라우팅입니다.</p>
              <div className="p-4 bg-gray-50 border-2 border-black border-dashed text-sm">
                <span className="font-bold block mb-1">로직</span>선언된 경로 규칙에 따라 브릭 사이 이동만 관찰합니다.
              </div>
            </div>
          </div>
          <div className="mt-6 pt-6 border-t-2 border-black">
            <div className="flex justify-between items-end space-x-2">
              <div className="font-headline font-bold flex-1">
                <span className="text-gray-600 block text-sm">{movementKo('forward')}</span>
                <span className="text-2xl md:text-3xl text-black">{forwardCount}<span className="text-sm md:text-lg">건</span></span>
              </div>
              <div className="font-headline font-bold flex-1 text-center">
                <span className="text-gray-600 block text-sm">{movementKo('reroute')}</span>
                <span className="text-2xl md:text-3xl text-black">{rerouteCount}<span className="text-sm md:text-lg">건</span></span>
              </div>
              <div className="font-headline font-bold flex-1 text-right">
                <span className="text-crimson block text-sm">{movementKo('stop')}</span>
                <span className="text-2xl md:text-3xl text-crimson">{lifecycleStopCount}<span className="text-sm md:text-lg">건</span></span>
              </div>
            </div>
          </div>
        </div>

        {/* 합류 */}
        <div className="border-4 border-black p-6 bg-white hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] transition-shadow duration-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-3 mb-4">
              <span className="material-symbols-outlined text-3xl text-black">merge_type</span>
              <h2 className="font-headline font-extrabold text-2xl tracking-tight">합류</h2>
            </div>
            <div className="space-y-4 font-body">
              <p className="text-gray-700">여러 갈래(병렬)의 브릭이 모두 도착해야 다음 단계가 열립니다. 분기(fan-out)로 갈라진 뒤 한 점으로 모입니다.</p>
              <div className="p-4 bg-gray-50 border-2 border-black border-dashed text-sm">
                <span className="font-bold block mb-1">로직</span>선행 브릭이 전부 모일 때까지 대기합니다.
              </div>
            </div>
          </div>
          <div className="mt-6 pt-6 border-t-2 border-black flex justify-between items-end">
            <div className="font-headline font-bold">
              <span className="text-gray-600 block text-sm">합류 지점이 있는 빌딩</span>
              <span className="text-3xl text-black">{fan.fan_in_buildings || 0}<span className="text-lg">개</span></span>
            </div>
            <div className="font-headline font-bold text-right">
              <span className="text-gray-500 block text-sm">분기 지점이 있는 빌딩</span>
              <span className="text-3xl text-gray-500">{fan.fan_out_buildings || 0}<span className="text-lg">개</span></span>
            </div>
          </div>
        </div>

        {/* 보류 */}
        <div className="border-4 border-black p-6 bg-white hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] transition-shadow duration-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-3 mb-4">
              <span className="material-symbols-outlined text-3xl text-black">front_hand</span>
              <h2 className="font-headline font-extrabold text-2xl tracking-tight">보류</h2>
            </div>
            <div className="space-y-4 font-body">
              <p className="text-gray-700">운영자 또는 호출자의 최종 처분이 내려질 때까지 넘김을 보관합니다.</p>
              <div className="p-4 bg-gray-50 border-2 border-black border-dashed text-sm">
                <span className="font-bold block mb-1">처분 주체별</span>
                {dispEntries.length ? (
                  <ul className="space-y-1">
                    {dispEntries.map(([o, v]) => (
                      <li key={o} className="flex justify-between"><span>{ownerKo(o)}</span><b className="font-black">{v}건</b></li>
                    ))}
                  </ul>
                ) : <span className="text-gray-500">현재 처분 대기 없음</span>}
              </div>
            </div>
          </div>
          <div className="mt-6 pt-6 border-t-2 border-black flex justify-between items-end">
            <div className="font-headline font-bold">
              <span className="text-gray-600 block text-sm">처분 주체 지정</span>
              <span className="text-3xl text-crimson">{dispTotal}<span className="text-lg">건</span></span>
            </div>
            <p className="text-gray-400 text-xs font-medium uppercase tracking-wider text-right self-end">설정 · 차후 지원</p>
          </div>
        </div>
      </div>
    </main>
  )
}
