export const defaultPracticeData = {
  courseName: 'Data Structures & Algorithms',
  courseMastery: 68,
  weakestTopic: {
    name: 'AVL Trees',
    mastery: 43,
  },
  adaptivePractice: {
    topic: 'AVL Trees',
    mastery: 43,
    statusText: 'Needs attention',
    badge: 'RECOMMENDED · ADAPTIVE PRACTICE',
    headline: 'Strengthen AVL Trees',
    description:
      'Your recent answers suggest difficulty with Left-Right and Right-Left rotations.',
    questionCount: 5,
    estimatedMinutes: 8,
    whyThis:
      'Edvora selected AVL Trees because your recent answers in the Tutor and Trees assessment showed difficulty resolving zigzag imbalances before balancing the root.',
  },
  quickPractice: {
    title: 'Quick Practice',
    description:
      'Practice for a few minutes across recent topics without configuring settings.',
    questionCount: 5,
    estimatedMinutes: 5,
    metadata: '~5 minutes · 5 mixed questions',
  },
  mockTest: {
    title: 'Mock Test',
    description:
      'Simulate a timed exam across all covered topics in this course.',
    metadata: 'Timed · Comprehensive · Exam conditions',
  },
  customOptions: {
    questionTypes: [
      { id: 'mixed', label: 'Mixed' },
      { id: 'mcq', label: 'MCQ' },
      { id: 'true_false', label: 'True / False' },
      { id: 'short_answer', label: 'Short Answer' },
      { id: 'numerical', label: 'Numerical' },
    ],
    topics: [
      { id: 'all', label: 'All Topics' },
      { id: 'arrays', label: 'Arrays' },
      { id: 'linked_lists', label: 'Linked Lists' },
      { id: 'trees', label: 'Trees & BST' },
      { id: 'avl', label: 'AVL Trees' },
    ],
    difficulties: [
      { id: 'adaptive', label: 'Adaptive (Recommended)' },
      { id: 'foundational', label: 'Foundational' },
      { id: 'standard', label: 'Standard' },
      { id: 'challenging', label: 'Challenging' },
    ],
    counts: [5, 10, 15, 20],
  },
  recentSessions: [
    {
      id: 'session-1',
      title: 'Trees assessment',
      subtitle: 'Binary trees, balanced trees and traversal fundamentals',
      score: 'Score 85%',
      variant: 'strong',
      time: 'Today',
      icon: 'check_circle',
      iconColor: 'text-[#34d399]',
    },
    {
      id: 'session-2',
      title: 'Binary Search Trees',
      subtitle: 'Insertion, search invariants, node deletion',
      score: 'Score 72%',
      variant: 'developing',
      time: 'Yesterday',
      icon: 'check_circle',
      iconColor: 'text-[#a78bfa]',
    },
    {
      id: 'session-3',
      title: 'AVL rotations',
      subtitle: 'Left-Right, Right-Left double rotations balance factors',
      score: 'Needs more practice',
      variant: 'attention',
      time: '2 days ago',
      icon: 'timelapse',
      iconColor: 'text-amber-400',
    },
  ],
};

