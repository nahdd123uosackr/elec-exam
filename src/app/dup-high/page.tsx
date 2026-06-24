'use client'
import QuizPage from '../../components/QuizPage'

export default function DupHighPage() {
  return <QuizPage config={{
    type: 'dup-high',
    title: '3회 이상 출제 문제',
    subtitle: '자주 출제되는 핵심 문제를 집중 공략하세요',
    icon: '🔁',
  }} />
}