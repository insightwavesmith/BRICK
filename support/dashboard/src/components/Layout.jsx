import { Link, useLocation } from 'react-router-dom'
import ParticipantPicker from './ParticipantPicker.jsx'

const menus = [
  { base: '/', to: '/', label: '프로젝트', icon: 'folder' },
  { base: '/building', to: '/building', label: '빌딩', icon: 'apartment' },
  { base: '/brick', to: '/brick', label: '브릭', icon: 'view_module' },
  { base: '/agent', to: '/agent', label: '에이전트', icon: 'group' },
  { base: '/link', to: '/link', label: '링크', icon: 'link' },
]

export default function Layout({ children }) {
  const { pathname } = useLocation()
  const active = (b) =>
    b === '/' ? pathname === '/' || pathname.startsWith('/project') : pathname.startsWith(b)
  return (
    <div className="min-h-screen bg-white text-ink flex flex-col md:flex-row">
      {/* 왼쪽 사이드바 (모바일에선 상단 아이콘바) */}
      <aside className="shrink-0 md:w-64 border-b md:border-b-0 md:border-r border-black/10 flex md:flex-col md:min-h-screen items-center md:items-stretch gap-2 md:gap-1.5 px-4 md:px-4 py-3 md:py-8 md:sticky md:top-0 md:self-start">
        <Link to="/" className="flex items-center gap-2 font-display font-black text-2xl md:text-3xl tracking-tight mr-4 md:mr-0 md:mb-10 md:px-1">
          <span className="w-4 h-4 md:w-5 md:h-5 bg-primary inline-block"></span>BRICK
        </Link>
        <nav className="flex md:flex-col gap-1 md:gap-1.5 flex-1 md:flex-none justify-end md:justify-start">
          {menus.map((m) => {
            const on = active(m.base)
            return (
              <Link key={m.label} to={m.to} title={m.label}
                className={`flex items-center gap-3 px-2 md:px-4 py-2 md:py-3 text-base md:text-lg font-display font-bold whitespace-nowrap border-l-4 transition-colors ${on ? 'border-primary text-primary bg-primary/5' : 'border-transparent text-black/55 hover:text-black hover:bg-black/[0.03]'}`}>
                <span className="material-symbols-outlined text-xl md:text-2xl">{m.icon}</span>
                <span className="hidden md:inline">{m.label}</span>
              </Link>
            )
          })}
        </nav>
        <span className="block md:mt-auto shrink-0 text-[10px] md:text-xs font-bold border border-black/20 px-2 md:px-3 py-1 text-black/55 whitespace-nowrap">읽기 전용</span>
      </aside>

      {/* 본문: 가운데 정렬 + 넓게 */}
      <main className="flex-1 min-w-0 px-6 md:px-12 py-10">
        <div className="max-w-7xl mx-auto">
          <ParticipantPicker />
          {children}
        </div>
      </main>
    </div>
  )
}
