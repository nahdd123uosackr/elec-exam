'use client'
import QuizPage from '../../components/QuizPage'

export default function SubjectPage() {
  return <QuizPage config={{
    type: 'subject',
    title: '과목별 문제 풀이',
    subtitle: '과목별로 분류된 문제를 학습하세요',
    icon: '📚',
  }} />
}