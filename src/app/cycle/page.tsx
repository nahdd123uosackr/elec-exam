'use client'
import QuizPage from '../../components/QuizPage'

export default function CyclePage() {
  return <QuizPage config={{
    type: 'cycle',
    title: '회차별 문제 풀이',
    subtitle: '원하는 회차를 선택해서 문제를 풀어보세요',
    icon: '📋',
  }} />
}