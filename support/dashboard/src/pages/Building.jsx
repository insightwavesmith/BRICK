import { useState, Fragment } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useDashboard } from '../data/useDashboard.js'
import { buildingKeyOf } from '../data/aggregate.js'
import { buildTimeline, pickFeatured } from '../data/graph.js'
import { dispKo, dispBadge } from '../data/labels.js'

function Avatar({ name, on }) {
  const ch = (name || '?').slice(0, 1).toUpperCase()
  return (
    <span className={`shrink-0 w-6 h-6 flex items-center justify-center text-xs font-black ${on ? 'bg-primary text-white' : name ? 'bg-black text-white' : 'bg-black/10 text-black/40'}`}>
      {ch}
    </span>
  )
}

function Card({ c }) {
  const now = c.status === 'now', done = c.status === 'done', wait = c.status === 'wait'
  return (
    <div className={`w-full bg-white p-4 ${now ? 'border-[3px] border-primary bg-[#C8153C]/[0.04] shadow-[6px_6px_0_#C8153C]' : done ? 'border-[3px] border-black' : 'border-2 border-black/20'}`}>
      <div className="flex items-center gap-2 mb-2.5">
        <div className={`font-headline font-black text-lg leading-tight break-all ${wait ? 'text-black/40' : ''}`}>{c.name}</div>
        {done && <span className="ml-auto material-symbols-outlined text-black/55">check</span>}
        {now && <span className="ml-auto w-2.5 h-2.5 bg-primary animate-pulse"></span>}
      </div>
      <div className={`flex items-center gap-2 ${wait ? 'opacity-40' : ''}`}>
        <Avatar name={c.agent} on={now} />
        <span className="text-sm font-bold">{c.agent || '미배정'}</span>
        <span className="text-[11px] text-black/40">담당 에이전트</span>
      </div>
    </div>
  )
}

function ParBlock({ row }) {
  const [open, setOpen] = useState(false)
  const anyNow = row.some((c) => c.status === 'now')
  const cluster = row.length >= 7
  return (
    <div className={`w-full border-2 border-dashed p-3 ${anyNow ? 'border-primary' : 'border-black/35'}`}>
      <div className="flex items-center mb-2">
        <span className="text-[11px] font-black text-black/45 tracking-wide">동시 진행 {row.length}{cluster && !open ? ' (묶음)' : ''}</span>
        {cluster && <button onClick={() => setOpen(!open)} className="ml-auto text-[11px] font-black underline">{open ? '접기 ▴' : '펼치기 ▾'}</button>}
      </div>
      {cluster && !open ? (
        <div className="flex flex-wrap gap-2">
          {Object.entries(row.reduce((a, c) => ((a[c.agent || '미배정'] = (a[c.agent || '미배정'] || 0) + 1), a), {})).map(([a, n]) => (
            <span key={a} className="inline-flex items-center gap-1.5 border-2 border-black px-2 py-1 text-xs font-bold">
              <Avatar name={a} /> {a} <b className="font-black">{n}</b>
            </span>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3">{row.map((c) => <Card key={c.ref} c={c} />)}</div>
      )}
    </div>
  )
}

function Gate({ gate }) {
  const m = {
    pass: { txt: '게이트 통과', cls: 'bg-black text-white border-black', ic: 'check', line: 'bg-primary', arr: 'text-primary' },
    wait: { txt: '게이트 대기', cls: 'bg-white text-black/45 border-black/30', ic: 'hourglass_empty', line: 'bg-black/20', arr: 'text-black/25' },
    stop: { txt: '게이트 멈춤', cls: 'bg-primary text-white border-black', ic: 'block', line: 'bg-primary', arr: 'text-primary' },
  }[gate.state] || { txt: '게이트', cls: 'bg-white border-black/30', ic: 'remove', line: 'bg-black/20', arr: 'text-black/25' }
  return (
    <div className="relative w-full flex flex-col items-center py-0.5">
      <div className={`w-1 h-3 ${m.line}`}></div>
      <span className={`inline-flex items-center gap-1 text-[11px] font-black px-2 py-1 border-2 ${m.cls}`}>
        <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>{m.ic}</span>{m.txt}
      </span>
      {gate.label && <span className="text-[10px] font-black text-black/45 mt-0.5">{gate.label}</span>}
      <span className={`material-symbols-outlined ${m.arr}`} style={{ fontSize: '26px', marginTop: '-2px' }}>arrow_downward</span>
    </div>
  )
}

export default function Building() {
  const { id } = useParams()
  const d = useDashboard()
  if (!d) return <div className="text-black/50 font-bold py-10">불러오는 중…</div>
  // 키 = (project, building_id) 복합. URL 의 id 가 복합키든 레거시 building_id 든
  // 같은 행/상세를 해석한다 (레거시 데이터는 building_id 단독 키 그대로).
  const detail = d.detail || {}
  const findRow = (k) => d.buildings.find((b) => buildingKeyOf(b) === k || b.id === k)
  let bid = (id && detail[id]) ? id : null
  if (!bid && id) {
    const row = findRow(id)
    if (row && detail[buildingKeyOf(row)]) bid = buildingKeyOf(row)
  }
  if (!bid) bid = pickFeatured(detail)
  const det = detail[bid]
  const building = findRow(bid)
  const projectLabel = (d.projects || []).find((p) => p.id === building?.project)?.label || building?.project
  const tl = buildTimeline(det, building)
  if (!tl) return <div className="text-black/50 font-bold py-10">표시할 그래프가 없습니다.</div>

  // boundary 줄(빌딩 닫힘)은 카드가 아니라 종료 표식으로 처리
  const bodyRows = tl.rows.filter((r) => !(r.length === 1 && r[0].boundary))
  const hasBoundary = tl.rows.some((r) => r.length === 1 && r[0].boundary)
  const nowCards = tl.rows.flat().filter((c) => c.status === 'now')
  const pending = building?.disp === 'closure_pending' || building?.disp === 'archived_stale'
  const total = tl.rows.flat().filter((c) => !c.boundary).length
  const doneN = tl.rows.flat().filter((c) => c.status === 'done').length

  return (
    <>
      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <Link to={building?.project ? `/project/${encodeURIComponent(building.project)}` : '/'} className="text-sm font-bold text-black/60">← 프로젝트로</Link>
        <h1 className="font-display font-black text-3xl md:text-4xl break-all">{building?.id || det?.name || bid}</h1>
        {projectLabel && <span className="bg-gray-100 border-2 border-black font-bold text-xs px-2 py-1">{projectLabel}</span>}
        <span className={`border-2 font-bold text-sm px-3 py-1 ${tl.closed ? dispBadge('closed') : dispBadge(building?.disp)}`}>
          {dispKo(building?.disp || building?.state)} · {tl.closed ? `브릭 ${total}개` : `${doneN}/${total} 브릭`}
        </span>
        {building?.stale && <span className="bg-gray-100 text-gray-600 border-2 border-gray-400 font-bold text-xs px-2 py-1">접어둠 · {building.ageDays}일 전 증거</span>}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        <div className="lg:col-span-2 border-4 border-black p-6 bg-[radial-gradient(#00000008_1px,transparent_1px)] [background-size:16px_16px]">
          <div className="font-headline font-black text-2xl mb-4 border-l-8 border-black pl-3">빌딩 시퀀스</div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mb-5 text-[11px] font-bold text-black/45">
            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-black inline-block"></span>완료</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 border-2 border-primary inline-block"></span>진행 중</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 border-2 border-black/20 inline-block"></span>대기</span>
            <span>게이트 = 링크(넘김) · 분기/합류 = 병렬</span>
          </div>
          <div className="flex flex-col items-center max-w-2xl mx-auto">
            {bodyRows.map((row, i) => (
              <Fragment key={i}>
                {row.length > 1 ? <ParBlock row={row} /> : <Card c={row[0]} />}
                {tl.gates[i] && <Gate gate={tl.gates[i]} />}
              </Fragment>
            ))}
            {hasBoundary && <div className="mt-3 text-[11px] font-bold text-black/35">▣ 빌딩 닫힘</div>}
          </div>
        </div>

        <aside className="border-4 border-black bg-white lg:sticky lg:top-4 shadow-[6px_6px_0_#000]">
          <div className="bg-black text-white p-3 font-headline font-bold flex items-center gap-2">
            <span className="material-symbols-outlined text-base">{tl.closed ? 'task_alt' : pending ? 'schedule' : 'sync'}</span>
            {tl.closed ? '빌딩 닫힘' : pending ? '마감 대기' : `지금 일어나는 일 (${nowCards.length})`}
          </div>
          <div className="p-4 space-y-3 max-h-[520px] overflow-y-auto">
            {tl.closed ? (
              <div className="text-sm text-black/50 font-bold">완료된 빌딩입니다. 진행 중 작업이 없습니다.</div>
            ) : pending ? (
              <div className="text-sm text-black/60 font-bold leading-relaxed">
                마지막 브릭까지 갔지만 <b>마감 도장이 안 찍힌</b> 상태입니다. 실행 중이 아니라 끝맺지 않은 것입니다.
                {building?.stale && <span className="block mt-2 text-yellow-700">마지막 증거가 {building.ageDays}일 전 — 정리(마감) 대상.</span>}
                {nowCards.length > 0 && <span className="block mt-2 text-black/45">멈춘 위치: {nowCards.map((c) => c.name).join(', ')}</span>}
              </div>
            ) : nowCards.length ? (
              nowCards.map((c) => (
                <div key={c.ref} className="border-2 border-black p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Avatar name={c.agent} on />
                    <span className="text-sm font-bold">{c.agent || '미배정'}</span>
                  </div>
                  <div className="font-bold break-all">{c.name}</div>
                </div>
              ))
            ) : (
              <div className="text-sm text-black/50 font-bold">현재 프론티어를 데이터에서 특정하지 못했습니다.</div>
            )}
            <div className="pt-2 mt-2 border-t border-black/10 text-[11px] text-black/40 leading-relaxed">
              구조(브릭·담당 에이전트·분기/합류)는 building-map 사실 그대로입니다. 완료/진행/대기는 빌딩 상태로 파생한 표시입니다.
            </div>
          </div>
        </aside>
      </div>
    </>
  )
}
