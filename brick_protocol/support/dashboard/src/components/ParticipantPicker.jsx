import { useParticipants } from '../data/useDashboard.js'

// 팀원 선택: 여러 사람이 자기 엔진에서 푸시하면 여기서 골라 "구경". 1명이면 그냥 누구 보는지 표시.
export default function ParticipantPicker() {
  const { participants, selectedRef, setSelected } = useParticipants()
  if (!participants.length) return null
  const multi = participants.length > 1
  return (
    <div className="flex items-center gap-2 mb-6">
      <span className="material-symbols-outlined text-black/45 text-lg">{multi ? 'groups' : 'visibility'}</span>
      <span className="text-sm font-bold text-black/45">보는 중</span>
      <select
        value={selectedRef || ''}
        onChange={(e) => setSelected(e.target.value)}
        className="border-2 border-black font-display font-bold text-sm px-3 py-1.5 bg-white cursor-pointer focus:outline-none focus:border-primary"
      >
        {participants.map((p) => (
          <option key={p.ref} value={p.ref}>{p.label}</option>
        ))}
      </select>
      {multi && <span className="text-xs font-bold text-black/40">팀원 {participants.length}명 · 골라서 구경</span>}
    </div>
  )
}
