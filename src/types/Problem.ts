export type Problem = {
  id: string
  문제: string
  정답?: string
  해설?: string
  사용공식?: string
  출처?: string
  회차?: string
  과목?: string
  난이도?: string
  보기?: string
  /** 콤마 구분 회차 목록 (예: '2017-03, 2019-03, 2021-02'). 비면 미중복. */
  중복출제?: string
}
