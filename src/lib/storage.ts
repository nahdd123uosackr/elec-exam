/**
 * 문제 풀이 기록(정답/오답)을 localStorage 에 영구 저장하고 조회하는 유틸리티
 */

export interface ProblemAttempt {
  problemId: string        // 문제 ID (UUID)
  lastPick: number         // 마지막 선택한 보기 번호 (1~5)
  isCorrect: boolean       // 최근 시도의 정답 여부
  lastAttemptAt: number    // 마지막 시도 시각 (Date.now())
  attemptCount: number     // 총 풀이 시도 횟수
  wrongCount: number       // 누적 틀린 횟수
}

export interface StorageData {
  version: 1
  updatedAt: number
  attempts: Record<string, ProblemAttempt>
}

const STORAGE_KEY = 'elec_exam_records_v1'
const STORAGE_EVENT = 'elec_exam_storage_change'

function getEmptyData(): StorageData {
  return {
    version: 1,
    updatedAt: Date.now(),
    attempts: {},
  }
}

/** 전체 풀이 기록 로드 (SSR 안전) */
export function getRecords(): Record<string, ProblemAttempt> {
  if (typeof window === 'undefined') return {}
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === 'object' && parsed.attempts) {
      return parsed.attempts as Record<string, ProblemAttempt>
    }
    return {}
  } catch (err) {
    console.warn('[storage] 기록 로드 실패, 초기화:', err)
    return {}
  }
}

/** 특정 문제 풀이 기록 조회 */
export function getRecord(problemId: string): ProblemAttempt | null {
  if (!problemId) return null
  const records = getRecords()
  return records[problemId] || null
}

function notifyChange() {
  if (typeof window === 'undefined') return
  try {
    window.dispatchEvent(new CustomEvent(STORAGE_EVENT))
  } catch {
    // 무시
  }
}

function writeData(attempts: Record<string, ProblemAttempt>): void {
  if (typeof window === 'undefined') return
  try {
    const data: StorageData = {
      version: 1,
      updatedAt: Date.now(),
      attempts,
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    notifyChange()
  } catch (err) {
    console.error('[storage] 기록 저장 실패:', err)
  }
}

/**
 * 풀이 시도 기록 저장
 * @param problemId 문제 UUID
 * @param pick 선택한 보기 번호 (1~5)
 * @param isCorrect 정답 여부
 */
export function saveAttempt(problemId: string, pick: number, isCorrect: boolean): ProblemAttempt {
  const records = getRecords()
  const prev = records[problemId]

  const attempt: ProblemAttempt = {
    problemId,
    lastPick: pick,
    isCorrect,
    lastAttemptAt: Date.now(),
    attemptCount: (prev?.attemptCount || 0) + 1,
    wrongCount: (prev?.wrongCount || 0) + (isCorrect ? 0 : 1),
  }

  records[problemId] = attempt
  writeData(records)
  return attempt
}

/**
 * 오답 문제 ID 목록 추출
 * @param options.onlyUnsolved true(기본값): 최근 시도가 오답인 문제, false: 한 번이라도 틀린 적 있는 문제
 */
export function getWrongProblemIds(options: { onlyUnsolved?: boolean } = {}): string[] {
  const { onlyUnsolved = true } = options
  const records = getRecords()
  const ids: string[] = []

  // 최근 시도순(내림차순)으로 정렬하여 반환
  const sorted = Object.values(records).sort((a, b) => b.lastAttemptAt - a.lastAttemptAt)

  for (const item of sorted) {
    if (onlyUnsolved) {
      if (!item.isCorrect) ids.push(item.problemId)
    } else {
      if (item.wrongCount > 0) ids.push(item.problemId)
    }
  }

  return ids
}

/** 특정 문제 기록 삭제 (오답 노트에서 제거 등) */
export function removeRecord(problemId: string): void {
  const records = getRecords()
  if (problemId in records) {
    delete records[problemId]
    writeData(records)
  }
}

/** 전체 풀이 기록 초기화 */
export function clearAllRecords(): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.removeItem(STORAGE_KEY)
    notifyChange()
  } catch (err) {
    console.error('[storage] 초기화 실패:', err)
  }
}

/** 통계 집계 */
export function getStorageStats(): {
  totalSolved: number
  totalCorrect: number
  totalWrong: number
  activeWrong: number
} {
  const records = getRecords()
  const values = Object.values(records)
  const totalSolved = values.length
  let totalCorrect = 0
  let totalWrong = 0
  let activeWrong = 0

  for (const item of values) {
    if (item.isCorrect) totalCorrect++
    else activeWrong++
    if (item.wrongCount > 0) totalWrong++
  }

  return { totalSolved, totalCorrect, totalWrong, activeWrong }
}

/**
 * 저장소 변경 구독 (동일 탭 커스텀 이벤트 + 다른 탭 storage 이벤트)
 * @returns cleanup 함수
 */
export function subscribeStorage(callback: () => void): () => void {
  if (typeof window === 'undefined') return () => {}

  const handleCustom = () => callback()
  const handleStorage = (e: StorageEvent) => {
    if (e.key === STORAGE_KEY || e.key === null) {
      callback()
    }
  }

  window.addEventListener(STORAGE_EVENT, handleCustom)
  window.addEventListener('storage', handleStorage)

  return () => {
    window.removeEventListener(STORAGE_EVENT, handleCustom)
    window.removeEventListener('storage', handleStorage)
  }
}
