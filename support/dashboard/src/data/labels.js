// 화면용 한글 라벨. 정본 데이터는 support/operator/label_map.json이고,
// reporter_notification_projection 커널 체크가 이 미러와의 parity를 검증한다.

// 브릭 종류 → 한글/아이콘. 키 = brick/templates/bricks/<kind>
export const BRICK = {
  plan: { ko: '계획', icon: 'architecture' },
  design: { ko: '설계', icon: 'design_services' },
  // KIND REVERT (0611, Smith): cto-assignment → development 복원(0610 rename은
  // 역할명이 kind에 들어간 axis smell). development = CTO 배분 기획 스텝, 코딩
  // 스텝은 work. cto-assignment 키는 하루짜리 창에 증거 행이 0건(전수 grep)이라
  // 별칭 없이 제거; 미지 키는 brickKo가 원문 그대로 표시한다.
  development: { ko: '개발 배분', icon: 'account_tree' },
  work: { ko: '작업', icon: 'build' },
  review: { ko: '검수', icon: 'fact_check' },
  inspect: { ko: '점검', icon: 'policy' },
  closure: { ko: '마감', icon: 'task_alt' },
  'axis-attack-qa': { ko: '축 공격 검수', icon: 'swords' },
  'code-attack-qa': { ko: '코드 공격 검수', icon: 'bug_report' },
  'evidence-integrity': { ko: '증거 무결성', icon: 'verified' },
}
export const brickKo = (k) => (BRICK[k] && BRICK[k].ko) || k
export const brickIcon = (k) => (BRICK[k] && BRICK[k].icon) || 'category'

// 에이전트 레인 → 한글
export const LANE = { leader: '리더', worker: '워커', reviewer: '리뷰어' }
export const laneKo = (l) => LANE[l] || l || '—'

// 도구정책(권한) → 한글
// WAVE-B (0610): leader-readonly → leader-coordination(리더 정책은 읽기 전용이
// 아니라 범위 내 쓰기 조율), review-readonly → reviewer-readonly. 옛 키는 과거
// 증거 행 표시용으로 유지(당시 법은 실제로 읽기 전용이었음).
export const TOOL = {
  'leader-coordination': '조율(범위 내 쓰기)',
  'read-write-scoped': '범위 내 쓰기',
  'reviewer-readonly': '읽기 전용',
  'leader-readonly': '읽기 전용', // historical
  'review-readonly': '읽기 전용', // historical
}
export const toolKo = (t) => TOOL[t] || t || '—'
export const canWrite = (t) => t === 'read-write-scoped'

// Link Movement → 한글 (정본: support/operator/label_map.json — 패리티 핀 대상)
// return/stop은 과거/수명주기 표시용 별칭; active Movement literal은 forward/reroute
export const MOVEMENT = {
  forward: '전진',
  reroute: '재지정',
  return: '재지정(과거 표기)',
  stop: '멈춤(수명주기)',
}
export const movementKo = (m) => MOVEMENT[m] || m || '—'

// 보드 상태(raw) → 한글
export const STATE = {
  closed: '완료',
  observed_running: '진행 중',
  link_paused: '멈춤',
  waiting_review: '검수 대기',
  evidence_incomplete: '데이터 미완',
  unknown: '상태 불명',
}
export const stateKo = (s) => STATE[s] || s || '상태 불명'

// 표시 상태(disp) → 한글. observed_running 을 frontier 로 쪼갠 결과까지 반영.
// running = 실제 작업 진행, closure_pending = 마감 도장만 안 찍힘(=열려있음)
export const DISP = {
  running: '진행 중',
  closure_pending: '마감 대기',
  archived_stale: '오래된 미마감',
  stopped: '멈춤',
  review: '검수 대기',
  incomplete: '데이터 미완',
  closed: '완료',
  unknown: '상태 불명',
}
export const dispKo = (s) => DISP[s] || s || '상태 불명'

// 처분 주체(disposition owner) → 한글
export const OWNER = {
  'caller-or-coo': '호출자 또는 COO',
  coo: 'COO',
  caller: '호출자',
}
export const ownerKo = (o) => OWNER[o] || o

// 빌딩 이벤트/알림 문구 → 한글. 정본은 label_map.json.
export const EVENT = {
  building_started: '시작',
  intervention_required: '멈춤·개입 필요',
  building_finished: '완료',
  state_observed: '상태 관찰',
}
export const eventKo = (e) => EVENT[e] || e

export const OBSERVED = {
  observed_started: '시작',
  observed_running: '진행 중',
  observed_closed_boundary: '완료',
  observed_paused: '멈춤·개입 필요',
  observed_human_gate: '멈춤·개입 필요',
  needs_disposition: '멈춤·개입 필요',
  observed_checker_failed: '점검 필요',
  observed_reporter_delivery_failed: '알림 확인 필요',
}
export const observedKo = (s) => OBSERVED[s] || s

export const ACTION = {
  building_started: '진행 상황 관찰',
  intervention_required: '처분 필요',
  building_finished: '알림 확인',
  state_observed: '상태 확인',
}
export const actionKo = (a) => ACTION[a] || a
