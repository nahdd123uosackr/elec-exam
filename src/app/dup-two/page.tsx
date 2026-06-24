'use client'
import QuizPage from '../../components/QuizPage'

export default function DupTwoPage() {
  return <QuizPage config={{
    type: 'dup-two',
    title: '2회 출제 문제',
    subtitle: '딱 한 번 더 출제된 문제로 실력을 확인하세요',
    icon: '🕑',
  }} />
}