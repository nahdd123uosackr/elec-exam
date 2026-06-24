'use client'
import QuizPage from '../../components/QuizPage'

export default function DupLowPage() {
  return <QuizPage config={{
    type: 'dup-low',
    title: '3회 미만 출제 문제',
    subtitle: '한 번 또는 두 번만 출제된 문제를 도전하세요',
    icon: '📖',
  }} />
}