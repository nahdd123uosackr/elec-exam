'use client'

import QuizPage from '../../components/QuizPage'

export default function WrongPage() {
  return (
    <QuizPage
      config={{
        type: 'wrong',
        title: '오답 문제 풀이',
        subtitle: '틀렸던 문제를 다시 풀고 취약점을 완벽히 보완하세요',
        icon: '📝',
      }}
    />
  )
}
