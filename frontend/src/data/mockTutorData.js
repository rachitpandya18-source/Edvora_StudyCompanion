export const defaultTutorSources = [
  {
    id: 'source-2',
    number: 2,
    type: 'PPT',
    typeColor: 'amber',
    title: 'Lecture 05 · Slide 18',
    location: 'Slide 18',
    actionText: 'Open slide →',
    diagram: {
      title: 'AVL Rebalance: Left-Right (LR) Case',
      condition: 'Condition: BF(Root) = +2 AND BF(LeftChild) = -1',
      rootNode: { val: '20', bf: 'BF: +2' },
      leftChild: { val: '10', bf: 'BF: -1' },
      elbowChild: { val: '15' },
    },
    quote:
      'When the height difference h(L) - h(R) > 1 and the left child is right-heavy, a Left rotation on child followed by Right rotation on parent restores height balance.',
  },
  {
    id: 'source-1',
    number: 1,
    type: 'PDF',
    typeColor: 'red',
    title: 'Trees.pdf · Page 42',
    location: 'Page 42',
    actionText: 'Open PDF →',
    quote:
      'Section 4.3: Mathematical definition of the Balance Invariant and proof of maximum tree height bounded by O(log n).',
  },
  {
    id: 'source-3',
    number: 3,
    type: 'VIDEO',
    typeColor: 'blue',
    title: 'Lecture 05 · 14:23',
    location: '14:23',
    actionText: 'Play from 14:23',
    isVideo: true,
    description:
      'Prof. Henderson explains the intuition behind elbow rotations on the chalkboard: "Think of it as straightening an elbow before leveling the shoulder."',
  },
];

export const initialTutorMessages = [
  {
    id: 'msg-1',
    sender: 'student',
    time: '10:42 AM',
    reference: 'Lecture_05 · Slide 18',
    text: 'Can you explain why we need a Double Rotation (Left-Right) in AVL Trees instead of a single rotation? Specifically looking at the diagram in Slide 18 of Lecture 5.',
  },
  {
    id: 'msg-2',
    sender: 'tutor',
    time: '10:42 AM',
    isGrounded: true,
    lead: 'A single rotation fails when the inserted node creates an "inner" elbow (Left-Right) imbalance. Because the node is inside the subtree, a single rotation simply shifts the imbalance laterally rather than decreasing tree height',
    leadCitation: 1,
    stepsHeading: 'Two-step resolution:',
    steps: [
      {
        num: 1,
        title: 'Left rotation on the child',
        desc: 'converts the zigzag (LR) into an outer straight line (LL)',
        citation: 2,
      },
      {
        num: 2,
        title: 'Right rotation on the root/parent',
        desc: 'restores the balance factor invariant',
        citation: 1,
      },
    ],
    diagramPreview: {
      title: 'Lecture 05 · Slide 18 — Visualizing LR Imbalance',
      tag: '[2] Slide 18',
      nodeRoot: 'Node 20 (BF: +2)',
      nodeChild: '↳ Child 10 (BF: -1)',
      nodeSubtree: '↳ Subtree 15',
      heightDiff: 'Subtree height difference: h = 3 vs h = 1.',
      instruction:
        'Click slide preview in right panel for step-by-step subtree rotation vectors.',
    },
    sourcesSummary: [
      { type: 'PDF', num: 1, label: 'Trees.pdf · P.42', sourceId: 'source-1' },
      { type: 'PPT', num: 2, label: 'Lecture_05_AVL.pptx · Slide 18', sourceId: 'source-2' },
      { type: 'VIDEO', num: 3, label: 'Lecture 05 · 14:23', sourceId: 'source-3' },
    ],
  },
  {
    id: 'msg-3',
    sender: 'student',
    time: '10:45 AM',
    text: 'How does Red-Black tree deletion compare to B-Trees in database index engines?',
  },
  {
    id: 'msg-4',
    sender: 'tutor-boundary',
    time: '10:45 AM',
    badge: 'Outside Your Course Material',
    noticeText:
      "I couldn't find B-Tree database indexing comparisons in the uploaded materials for this course. This course focuses primarily on in-memory binary search structures (AVL, Red-Black).",
    promptText:
      'Would you like me to answer using general computer science knowledge, or keep strictly to your exam syllabus?',
  },
];

export const generalKnowledgeAnswer = {
  id: 'msg-gk',
  sender: 'tutor-general',
  time: 'Just now',
  badge: 'GENERAL KNOWLEDGE',
  text:
    'In general computer science and database internals:\n\n1. Red-Black Trees are binary search trees designed for fast, in-memory pointer lookups with O(log n) time per node operation.\n\n2. B-Trees and B+ Trees are multi-way balanced trees optimized for secondary disk storage and block I/O. They group thousands of keys into single disk pages (e.g., 4KB or 16KB blocks) to minimize high-latency random disk reads in engines like PostgreSQL, MySQL InnoDB, and SQLite.',
  note: 'This answer uses general computing knowledge and is not cited from your course syllabus.',
};

export const courseOnlyAnswer = {
  id: 'msg-co',
  sender: 'tutor-course-only',
  time: 'Just now',
  badge: 'COURSE SYLLABUS FOCUS',
  text:
    'Staying within your course syllabus:\n\nYour course covers AVL Trees and Red-Black tree properties for in-memory operations. We can review Red-Black tree coloring rules, insertion rebalancing cases, or continue with AVL Tree rotations whenever you are ready.',
  note: 'Filtered strictly to your uploaded lecture slides and textbook materials.',
};

