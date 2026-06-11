import { useDashboard } from '../data/useDashboard.js'
import { ownerKo } from '../data/labels.js'

export default function LinkPage() {
  const d = useDashboard()
  if (!d) return <main className="max-w-7xl mx-auto px-6 py-12 text-black/50 font-bold">불러오는 중…</main>
  const mv = d.links?.movement || {}
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
              <h2 className="font-headline font-extrabold text-2xl tracking-tight">충분성 (Sufficiency)</h2>
            </div>
            <div className="space-y-4 font-body">
              <p className="text-gray-700">다음 단계로 넘기기 전, 필요한 사실(증거)이 모두 모였는지 검증합니다. 부족하면 전진 대신 멈춤으로 갑니다.</p>
              <div className="p-4 bg-gray-50 border-2 border-black border-dashed text-sm">
                <span className="font-bold block mb-1">집계 위치</span>
                멈춤 여부는 아래 ‘움직임’에 함께 집계됩니다(이 스냅샷엔 충분성 단독 카운터 없음).
              </div>
            </div>
          </div>
          <div className="mt-6 pt-6 border-t-2 border-black flex justify-between items-end">
            <div className="font-headline font-bold">
              <span className="text-gray-600 block text-sm">멈춤(전진 보류)</span>
              <span className="text-3xl text-crimson">{mv.stop || 0}<span className="text-lg">건</span></span>
            </div>
            <p className="text-gray-400 text-xs font-medium uppercase tracking-wider text-right self-end">설정 · 차후 지원</p>
          </div>
        </div>

        {/* 움직임 */}
        <div className="border-4 border-black p-6 bg-white hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] transition-shadow duration-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-3 mb-4">
              <span className="material-symbols-outlined text-3xl text-black">arrow_forward</span>
              <h2 className="font-headline font-extrabold text-2xl tracking-tight">움직임 (Movement)</h2>
            </div>
            <div className="space-y-4 font-body">
              <p className="text-gray-700">각 빌딩의 가장 최근 링크 판정입니다. 전진 · 되돌림 · 멈춤 셋 중 하나입니다.</p>
              <div className="p-4 bg-gray-50 border-2 border-black border-dashed text-sm">
                <span className="font-bold block mb-1">로직</span>사전에 정의된 경로 규칙에 따라 브릭을 전송하거나 멈춥니다.
              </div>
            </div>
          </div>
          <div className="mt-6 pt-6 border-t-2 border-black">
            <div className="flex justify-between items-end space-x-2">
              <div className="font-headline font-bold flex-1">
                <span className="text-gray-600 block text-sm">전진</span>
                <span className="text-2xl md:text-3xl text-black">{mv.forward || 0}<span className="text-sm md:text-lg">건</span></span>
              </div>
              <div className="font-headline font-bold flex-1 text-center">
                <span className="text-gray-600 block text-sm">되돌림</span>
                <span className="text-2xl md:text-3xl text-black">{mv.return || 0}<span className="text-sm md:text-lg">건</span></span>
              </div>
              <div className="font-headline font-bold flex-1 text-right">
                <span className="text-crimson block text-sm">멈춤</span>
                <span className="text-2xl md:text-3xl text-crimson">{mv.stop || 0}<span className="text-sm md:text-lg">건</span></span>
              </div>
            </div>
          </div>
        </div>

        {/* 합류 */}
        <div className="border-4 border-black p-6 bg-white hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] transition-shadow duration-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-3 mb-4">
              <span className="material-symbols-outlined text-3xl text-black">merge_type</span>
              <h2 className="font-headline font-extrabold text-2xl tracking-tight">합류 (Fan-in)</h2>
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
              <h2 className="font-headline font-extrabold text-2xl tracking-tight">보류 (HOLD)</h2>
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
