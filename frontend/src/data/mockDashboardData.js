export const mockStudentProfile = {
  name: "Alex Rivera",
  initials: "AR",
  program: "Computer Science",
  year: "Class of 2026",
  status: "Active",
};

export const mockQuickStartActions = [
  {
    id: "continue",
    category: "CONTINUE",
    title: "Continue learning",
    subtitle: "Data Structures · AVL Trees",
    icon: "play_arrow",
    target: "workspace",
    courseId: "cs201",
    accentColor: "accent",
  },
  {
    id: "tutor",
    category: "ASK TUTOR",
    title: "Ask your tutor",
    subtitle: "Ask about your course",
    icon: "chat_bubble",
    target: "workspace_tutor",
    courseId: "cs201",
    accentColor: "surface",
  },
  {
    id: "practice",
    category: "PRACTICE",
    title: "Practice weak topics",
    subtitle: "3 concepts need attention",
    icon: "psychology",
    target: "workspace_practice",
    courseId: "cs201",
    accentColor: "attention",
  },
  {
    id: "materials",
    category: "RESOURCES",
    title: "Browse materials",
    subtitle: "View your course resources",
    icon: "description",
    target: "workspace_materials",
    courseId: "cs201",
    accentColor: "surface",
  },
];

export const mockCourses = [
  {
    id: "cs201",
    code: "CS 201",
    title: "Data Structures",
    category: "Algorithms & Data Structures",
    mastery: 68,
    statusText: "Needs attention",
    statusVariant: "attention", // "attention" | "strong" | "developing"
    statusColor: "#fbbf24",
    currentlyLearning: "AVL Trees (Self-Balancing)",
    lastStudied: "Today · 14 min ago",
    materials: {
      textbooks: 3,
      slides: 14,
      lectures: 8,
    },
    primaryAction: "Continue",
  },
  {
    id: "cs340",
    code: "CS 340",
    title: "DBMS",
    category: "Database Management Systems",
    mastery: 82,
    statusText: "On track",
    statusVariant: "strong",
    statusColor: "#34d399",
    currentlyLearning: "Normalization (BCNF & 3NF)",
    lastStudied: "Yesterday · 4:15 PM",
    materials: {
      textbooks: 1,
      slides: 9,
      lectures: 6,
    },
    primaryAction: "Continue",
  },
  {
    id: "cs312",
    code: "CS 312",
    title: "Operating Systems",
    category: "System Architecture & Concurrency",
    mastery: 54,
    statusText: "Developing",
    statusVariant: "developing",
    statusColor: "#71717a",
    currentlyLearning: "Virtual Memory & Page Tables",
    lastStudied: "3 days ago",
    materials: {
      textbooks: 2,
      slides: 11,
      lectures: 5,
    },
    primaryAction: "Continue",
  },
];

export const mockStudyNext = {
  courseId: "cs201",
  courseCode: "CS 201",
  courseName: "Data Structures",
  topic: "AVL Trees",
  mastery: 43,
  status: "Needs attention",
  rationale: "Recent assessment responses show difficulty with Left-Right and Right-Left double rotations.",
  recommendedActions: [
    {
      id: 1,
      step: 1,
      title: "Review AVL rotations summary",
      durationOrPage: "4 min",
      type: "summary",
    },
    {
      id: 2,
      step: 2,
      title: "Review course material (Trees.pdf)",
      durationOrPage: "p. 42",
      type: "pdf",
    },
    {
      id: 3,
      step: 3,
      title: "Practice 3 targeted questions",
      durationOrPage: "5 min",
      type: "quiz",
    },
  ],
};

export const mockRecentActivity = [
  {
    id: "act-1",
    title: "Completed Trees assessment",
    course: "Data Structures",
    detail: "Scored 85%",
    time: "Today · 20 min ago",
    icon: "check",
    variant: "strong",
  },
  {
    id: "act-2",
    title: "Asked tutor about AVL rotations",
    course: "Data Structures",
    detail: "3 sources cited",
    time: "Today · 45 min ago",
    icon: "chat",
    variant: "accent",
  },
  {
    id: "act-3",
    title: "Reviewed Binary Search Trees",
    course: "Data Structures",
    detail: "Trees.pdf (Ch. 4)",
    time: "Yesterday",
    icon: "menu_book",
    variant: "neutral",
  },
];

export const mockOverallSnapshot = {
  strongCount: 8,
  developingCount: 5,
  attentionCount: 3,
};

