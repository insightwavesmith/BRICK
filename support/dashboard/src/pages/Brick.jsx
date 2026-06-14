import { useDashboard } from '../data/useDashboard.js'
import { brickKo, brickIcon } from '../data/labels.js'

export default function Brick() {
  const d = useDashboard()
  if (!d) return <main className="container mx-auto px-6 py-12 text-black/50 font-bold">불러오는 중…</main>
  const bricks = d.bricks || []
  return (
    <main className="flex-grow container mx-auto px-6 py-12 max-w-6xl">
      <header className="mb-12 border-b-4 border-black pb-8">
        <h1 className="text-3xl md:text-4xl font-black font-headline tracking-tight mb-4 text-black">브릭 카탈로그</h1>
        <p className="text-xl font-medium text-gray-800 max-w-3xl leading-relaxed">
          단일 기능 블록(브릭)의 종류와 역할입니다. 각 브릭은 명확한 권한과 반환값(증거)을 가집니다.
          <span className="text-gray-500"> · 총 {bricks.length}종 · 쓰기 가능 브릭은 ‘작업’ 하나뿐</span>
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {bricks.map((b) => {
          const w = b.write
          const ret = (b.returnShape || '').split(',').map((s) => s.trim()).filter(Boolean)
          return (
            <article key={b.kind}
              className={`brick-card border-4 transition-transform duration-200 ease-in-out hover:-translate-x-1 hover:-translate-y-1 p-6 flex flex-col justify-between h-full ${w ? 'border-[#C8153C] bg-red-50 hover:shadow-[8px_8px_0px_#C8153C]' : 'border-black bg-white hover:shadow-[8px_8px_0px_#000000]'}`}>
              <div>
                <div className={`flex justify-between items-start border-b-2 pb-4 mb-4 ${w ? 'border-[#C8153C] text-[#C8153C]' : 'border-black'}`}>
                  <h2 className="text-2xl font-black font-headline tracking-tight">{brickKo(b.kind)}</h2>
                  <span className="material-symbols-outlined text-3xl" style={w ? { fontVariationSettings: "'FILL' 1" } : undefined}>{brickIcon(b.kind)}</span>
                </div>
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-xs bg-black text-white px-2 py-1 uppercase tracking-wider">종류</span>
                    <span className="font-mono text-sm text-gray-600">{b.kind}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`font-bold text-xs px-2 py-1 uppercase tracking-wider border ${w ? 'border-[#C8153C] text-[#C8153C] bg-white' : 'bg-gray-200 text-black border-black'}`}>권한</span>
                    <span className={`font-semibold ${w ? 'font-black text-[#C8153C]' : 'text-gray-700'}`}>{w ? '쓰기 가능' : '읽기 전용'}</span>
                  </div>
                </div>
              </div>
              <div className={`mt-6 pt-4 border-t border-dashed ${w ? 'border-[#C8153C]' : 'border-gray-400'}`}>
                <span className={`text-xs font-bold uppercase tracking-widest block mb-2 ${w ? 'text-[#C8153C]' : 'text-gray-500'}`}>반환(증거)</span>
                <div className="flex flex-wrap gap-1.5">
                  {ret.map((f) => (
                    <span key={f} className="text-[11px] font-mono bg-black/5 border border-black/15 px-1.5 py-0.5">{f}</span>
                  ))}
                </div>
              </div>
            </article>
          )
        })}
      </div>
    </main>
  )
}
