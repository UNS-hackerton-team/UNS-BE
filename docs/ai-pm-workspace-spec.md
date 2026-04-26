# AI PM Workspace MVP Spec

## 1. 서비스 한 줄 소개
팀원의 프로젝트별 역할과 역량을 분석해 AI가 업무를 생성하고 가장 적합한 담당자를 추천하는 실행 중심 협업 워크스페이스.

## 2. 문제 정의
- 해커톤과 팀 프로젝트에서는 초반 업무 분해와 역할 배정에 시간이 많이 든다.
- PM 역할이 비어 있으면 회의 내용이 실제 실행 태스크로 전환되지 않는다.
- 기존 협업툴은 프로젝트마다 달라지는 역할과 역량을 반영하지 못한다.
- 스프린트와 우선순위 관리가 수동적이라 실제 개발 시간이 줄어든다.

## 3. 해결 방법
- 워크스페이스 안에서 프로젝트를 만들고 프로젝트별 참여 프로필을 받는다.
- AI가 프로젝트 설명, 목표, 기술 스택, 팀원 프로필을 읽고 백로그 태스크를 생성한다.
- 별점 기반 적합도 계산으로 담당자 후보를 추천하고 PM이 최종 확정한다.
- 공유 AI 채팅은 프로젝트 방향과 우선순위를 조정하고, 개인 AI 채팅은 각자 할 일을 쪼개 준다.

## 4. 주요 사용자
- `OWNER`: 워크스페이스 생성자. 초대 링크와 팀원 관리 담당.
- `PM`: 프로젝트 생성, 스프린트 관리, AI 업무 배정 최종 승인 담당.
- `MEMBER`: 프로젝트 참여 프로필 입력, 배정된 이슈 수행, AI 채팅 사용.

## 5. 워크스페이스 초대 방식
- 워크스페이스 생성 시 `inviteCode`가 자동 발급된다.
- 초대 링크 형식은 `/invite/{inviteCode}` 또는 API 기준 `/api/v1/invites/{inviteCode}`이다.
- 팀원은 초대 링크 검증 후 로그인 또는 회원가입을 거쳐 워크스페이스에 참여한다.
- MVP는 워크스페이스당 단일 초대 코드와 복사 중심 흐름을 사용한다.

## 6. 핵심 기능 정리
- 회원가입/로그인
- 워크스페이스 생성 및 초대 링크 참여
- 프로젝트 생성
- 프로젝트 참여 프로필 등록
- AI 태스크 생성
- 별점 기반 업무 배정 추천 및 확정
- 백로그 조회/수정
- 스프린트 생성 및 이슈 연결
- 이슈 상태 변경
- 프로젝트 대시보드
- AI PM 공유 채팅방
- 개인 AI 채팅방

## 7. 화면 구조
### 7.1 필수 화면
- 랜딩 페이지
  - 소개 문구, 로그인, 회원가입, 워크스페이스 생성 CTA
- 회원가입 페이지
  - 입력: 이름, 이메일, 비밀번호
  - 버튼: 회원가입
- 로그인 페이지
  - 입력: 이메일, 비밀번호
  - 버튼: 로그인
- 워크스페이스 생성 페이지
  - 입력: 워크스페이스 이름, 설명, 팀/회사 유형
  - 버튼: 워크스페이스 생성하기
- 워크스페이스 초대 링크 페이지
  - 표시: 워크스페이스 이름, 초대 링크, 링크 상태, 참여 팀원 수
  - 버튼: 초대 링크 복사, 초대 링크 재발급, 초대 링크 비활성화, 프로젝트 만들기
- 초대 수락 페이지
  - 표시: `{workspaceName} 워크스페이스에 초대되었습니다`
  - 버튼: 로그인하고 참여하기, 회원가입하고 참여하기
- 프로젝트 목록 페이지
  - 표시: 프로젝트 카드, PM, 기간, 우선순위
  - 버튼: 프로젝트 생성
- 프로젝트 생성 페이지
  - 입력: 이름, 설명, 목표, 기간, 기술 스택, 우선순위, MVP 범위
  - 버튼: 프로젝트 생성
- 프로젝트 참여 프로필 입력 페이지
  - 입력: 역할, 기술 스택, 자신 있는 업무, 선호하지 않는 업무, 하루 가능 시간, 경험 수준
  - 버튼: 참여 프로필 저장
- 프로젝트 대시보드
  - 표시: 전체 이슈 수, 완료 수, 진행 중 수, 스프린트 진행률, 병목 분석, 추천 다음 이슈
- 팀원 목록 페이지
  - 표시: 이름, 워크스페이스 역할, 프로젝트 역할, 기술 스택, 가용 시간
- AI PM 공유 채팅방
  - 표시: 메시지 목록, 구조화 응답 카드
  - 버튼: 메시지 전송
- 개인 AI 채팅방
  - 표시: 현재 담당 이슈, 추천 작업 순서
  - 버튼: 메시지 전송
- 백로그 페이지
  - 표시: 백로그 리스트, 우선순위, 난이도, 예상 시간, 추천 역할
  - 버튼: AI로 태스크 생성, 백로그 추가
- 스프린트 페이지
  - 표시: 스프린트 목록, 상태, 포함 이슈
  - 버튼: 스프린트 생성, 이슈 추가
- 이슈 상세 페이지
  - 표시: 제목, 설명, 담당자, 상태, 우선순위, 난이도, 기술 스택
  - 버튼: 상태 변경, 담당자 변경
- 업무 자동 배정 결과 페이지
  - 표시: 태스크별 추천 담당자, 후보별 별점, 배정 이유
  - 버튼: 배정 확정

## 8. 데이터 모델
### 8.1 User
- `id`
- `name`
- `email`
- `passwordHash`
- `createdAt`

### 8.2 Workspace
- `id`
- `name`
- `description`
- `teamType`
- `ownerId`
- `inviteCode`
- `inviteCodeActive`
- `inviteCodeExpiresAt`
- `inviteCodeMaxUses`
- `inviteCodeUsedCount`
- `createdAt`

### 8.3 WorkspaceMember
- `id`
- `workspaceId`
- `userId`
- `workspaceRole`
- `joinedAt`

### 8.4 Project
- `id`
- `workspaceId`
- `name`
- `description`
- `goal`
- `techStack`
- `startDate`
- `endDate`
- `pmId`
- `priority`
- `mvpScope`
- `createdAt`

### 8.5 ProjectMember
- `id`
- `projectId`
- `userId`
- `projectRole`
- `techStack`
- `strongTasks`
- `dislikedTasks`
- `availableHoursPerDay`
- `experienceLevel`
- `joinedAt`

### 8.6 BacklogItem
- `id`
- `projectId`
- `title`
- `description`
- `priority`
- `requiredRole`
- `requiredTechStack`
- `difficulty`
- `estimatedHours`
- `status`
- `linkedIssueId`
- `createdAt`

### 8.7 Sprint
- `id`
- `projectId`
- `name`
- `goal`
- `startDate`
- `endDate`
- `status`
- `createdAt`

### 8.8 Issue
- `id`
- `projectId`
- `sprintId`
- `backlogItemId`
- `assigneeId`
- `title`
- `description`
- `status`
- `priority`
- `difficulty`
- `estimatedHours`
- `requiredRole`
- `requiredTechStack`
- `assignmentReason`
- `dueDate`
- `createdBy`
- `createdAt`

### 8.9 ChatRoom
- `id`
- `projectId`
- `type`
- `userId`
- `createdAt`

### 8.10 ChatMessage
- `id`
- `chatRoomId`
- `senderId`
- `senderType`
- `content`
- `metadata`
- `createdAt`

## 9. API 설계 초안
### 9.1 인증
- `POST /api/v1/auth/signup`
  - Request: `{ "name": "", "email": "", "password": "" }`
  - Response: `{ "access_token": "", "token_type": "bearer", "user": { "id": 1, "name": "", "email": "" } }`
  - 권한: 공개
- `POST /api/v1/auth/login`
  - Request: `{ "email": "", "password": "" }`
  - Response: `signup`과 동일
  - 권한: 공개
- `GET /api/v1/auth/me`
  - Response: 현재 사용자
  - 권한: 로그인 사용자

### 9.2 워크스페이스/초대
- `POST /api/v1/workspaces`
  - Request: `{ "name": "", "description": "", "team_type": "" }`
  - Response: 워크스페이스 상세
  - 권한: 로그인 사용자
- `GET /api/v1/workspaces/{workspaceId}`
  - Response: 워크스페이스 상세
  - 권한: 워크스페이스 멤버
- `GET /api/v1/workspaces/{workspaceId}/invite`
  - Response: `{ "workspace_id": 1, "workspace_name": "", "invite_code": "", "invite_url": "", ... }`
  - 권한: 워크스페이스 멤버
- `PATCH /api/v1/workspaces/{workspaceId}/invite/regenerate`
  - Request: `{ "expires_at": null, "max_uses": null }`
  - Response: 초대 링크 정보
  - 권한: OWNER
- `PATCH /api/v1/workspaces/{workspaceId}/invite/deactivate`
  - Response: 초대 링크 정보
  - 권한: OWNER
- `GET /api/v1/invites/{inviteCode}`
  - Response: `{ "valid": true, "workspace_id": 1, "workspace_name": "", "message": "" }`
  - 권한: 공개
- `POST /api/v1/invites/{inviteCode}/join`
  - Response: `{ "workspace_id": 1, "workspace_name": "", "joined": true, "workspace_role": "MEMBER" }`
  - 권한: 로그인 사용자

### 9.3 프로젝트
- `POST /api/v1/workspaces/{workspaceId}/projects`
  - Request: 프로젝트 생성 정보
  - Response: 프로젝트 상세
  - 권한: 워크스페이스 멤버
- `GET /api/v1/workspaces/{workspaceId}/projects`
  - Response: 프로젝트 배열
  - 권한: 워크스페이스 멤버
- `GET /api/v1/projects/{projectId}`
  - Response: 프로젝트 상세
  - 권한: 워크스페이스 멤버

### 9.4 프로젝트 참여 프로필
- `POST /api/v1/projects/{projectId}/members/profile`
  - Request: `{ "project_role": "", "tech_stack": [], "strong_tasks": [], "disliked_tasks": [], "available_hours_per_day": 6, "experience_level": "INTERMEDIATE" }`
  - Response: 참여 프로필
  - 권한: 프로젝트 멤버
- `PATCH /api/v1/projects/{projectId}/members/profile`
  - Request: 동일
  - Response: 참여 프로필
  - 권한: 프로젝트 멤버
- `GET /api/v1/projects/{projectId}/members`
  - Response: 팀원 목록과 프로젝트 참여 프로필
  - 권한: 프로젝트 멤버

### 9.5 AI 기능
- `POST /api/v1/projects/{projectId}/ai/tasks`
  - Request: `{ "create_backlog": true }`
  - Response: `{ "project_summary": "", "tasks": [...], "created_backlog_items": [1,2] }`
  - 권한: PM
- `POST /api/v1/projects/{projectId}/ai/assignments`
  - Request: `{ "backlog_item_ids": [1,2] }`
  - Response: 태스크별 추천 담당자, 별점, 이유
  - 권한: 프로젝트 멤버
- `POST /api/v1/projects/{projectId}/ai/assignments/confirm`
  - Request: `{ "assignments": [{ "backlog_item_id": 1, "assignee_id": 2, "assignment_reason": "", "sprint_id": null }] }`
  - Response: `{ "created_issue_ids": [3,4] }`
  - 권한: PM

### 9.6 백로그
- `GET /api/v1/projects/{projectId}/backlog`
  - Response: 백로그 배열
  - 권한: 프로젝트 멤버
- `POST /api/v1/projects/{projectId}/backlog`
  - Request: 백로그 생성 정보
  - Response: 생성된 백로그
  - 권한: PM
- `PATCH /api/v1/backlog/{backlogItemId}`
  - Request: 부분 수정
  - Response: 수정된 백로그
  - 권한: PM
- `DELETE /api/v1/backlog/{backlogItemId}`
  - Response: 없음
  - 권한: PM

### 9.7 스프린트/이슈
- `POST /api/v1/projects/{projectId}/sprints`
  - Request: `{ "name": "", "goal": "", "start_date": "", "end_date": "" }`
  - Response: 스프린트
  - 권한: PM
- `GET /api/v1/projects/{projectId}/sprints`
  - Response: 스프린트 배열
  - 권한: 프로젝트 멤버
- `POST /api/v1/sprints/{sprintId}/issues`
  - Request: `{ "issue_ids": [1,2] }`
  - Response: 스프린트
  - 권한: PM
- `POST /api/v1/projects/{projectId}/issues`
  - Request: 이슈 생성 정보
  - Response: 이슈 상세
  - 권한: 프로젝트 멤버
- `PATCH /api/v1/issues/{issueId}/status`
  - Request: `{ "status": "IN_PROGRESS" }`
  - Response: 수정된 이슈
  - 권한: 담당자 또는 PM
- `PATCH /api/v1/issues/{issueId}/assignee`
  - Request: `{ "assignee_id": 2, "assignment_reason": "" }`
  - Response: 수정된 이슈
  - 권한: PM

### 9.8 대시보드/채팅
- `GET /api/v1/projects/{projectId}/dashboard`
  - Response: 이슈 통계, 팀 업무량, 병목 분석, 추천 다음 이슈
  - 권한: 프로젝트 멤버
- `POST /api/v1/projects/{projectId}/chat/team/messages`
  - Request: `{ "content": "" }`
  - Response: 구조화된 AI 응답
  - 권한: 프로젝트 멤버
- `POST /api/v1/projects/{projectId}/chat/personal/messages`
  - Request: `{ "content": "" }`
  - Response: 개인화된 AI 응답
  - 권한: 프로젝트 멤버

## 10. AI 프롬프트 설계
모든 AI 응답은 JSON으로 반환한다.

### 10.1 프로젝트 분석 프롬프트
```text
You are an AI PM. Analyze the following project and return JSON only.
Input:
- project_name
- project_description
- project_goal
- tech_stack
- mvp_scope
- team_members[]
Output JSON:
{
  "summary": "",
  "core_user_flow": [],
  "major_risks": [],
  "missing_information": [],
  "recommended_first_actions": []
}
```

### 10.2 태스크 자동 생성 프롬프트
```text
You are an AI PM that creates execution-ready backlog items.
Input:
- project_name
- project_description
- project_goal
- tech_stack
- mvp_scope
- team_members[]
Return JSON only:
{
  "tasks": [
    {
      "title": "",
      "description": "",
      "required_role": "",
      "required_tech_stack": [],
      "difficulty": "LOW|MEDIUM|HIGH",
      "estimated_hours": 1,
      "priority": "LOW|MEDIUM|HIGH"
    }
  ]
}
```

### 10.3 별점 기반 업무 배정 프롬프트
```text
You are an AI PM allocator. For each task, score every member.
Input:
- task
- team_members[]
- current_workload[]
Scoring rules:
- role_match +2
- each_tech_match +1 up to 2
- strong_task_match +2
- disliked_task_conflict -2
- low_workload +1
- enough_available_hours +1
- experience_fit +1
Return JSON only:
{
  "assignments": [
    {
      "task_title": "",
      "candidates": [
        {
          "user_id": 1,
          "score": 5,
          "stars": "★★★★★",
          "reasons": []
        }
      ],
      "recommended_assignee_id": 1,
      "recommendation_reason": ""
    }
  ]
}
```

### 10.4 AI PM 공유 채팅방 프롬프트
```text
You are the shared AI PM for a team workspace.
Use:
- project summary
- backlog
- issues
- sprint status
- team workload
Answer in JSON only:
{
  "summary": "",
  "recommended_tasks": [],
  "risks": [],
  "next_action": "",
  "priority": "LOW|MEDIUM|HIGH",
  "reasoning": ""
}
```

### 10.5 개인 AI 채팅방 프롬프트
```text
You are a personal AI work coach for one project member.
Use:
- assigned issues
- member project profile
- current sprint
Return JSON only:
{
  "summary": "",
  "current_assignments": [],
  "recommended_order": [],
  "top_priority_issue": {},
  "blocking_questions": []
}
```

### 10.6 스프린트 추천 프롬프트
```text
You are an AI PM planning the next sprint.
Use:
- backlog
- issue status
- project goal
- team capacity
Return JSON only:
{
  "sprint_goal": "",
  "recommended_issue_ids": [],
  "why_these_issues": [],
  "risks": []
}
```

### 10.7 대시보드 병목 분석 프롬프트
```text
You are an AI PM identifying delivery bottlenecks.
Use:
- issue counts by status
- workload by member
- role distribution
- due dates
Return JSON only:
{
  "bottleneck_summary": "",
  "risk_issues": [],
  "overloaded_members": [],
  "recommended_next_issue": {},
  "actions": []
}
```

## 11. 별점 알고리즘 설계
- 역할 일치: `+2`
- 기술 스택 일치: `+1`씩 최대 `+2`
- 자신 있는 업무 일치: `+2`
- 선호하지 않는 업무 충돌: `-2`
- 현재 업무량이 적음: `+1`
- 하루 작업 가능 시간이 충분함: `+1`
- 경험 수준이 난이도와 적합함: `+1`

별점 변환:
- `0~1`: `★☆☆☆☆`
- `2`: `★★☆☆☆`
- `3`: `★★★☆☆`
- `4`: `★★★★☆`
- `5 이상`: `★★★★★`

## 12. 핵심 사용자 플로우
1. 사용자가 이름, 이메일, 비밀번호로 회원가입한다.
2. 방장이 워크스페이스를 생성한다.
3. 방장이 초대 링크를 복사해 팀원에게 공유한다.
4. 팀원이 초대 링크에서 로그인 또는 회원가입 후 워크스페이스에 참여한다.
5. PM이 프로젝트를 생성한다.
6. 팀원이 프로젝트별 참여 프로필을 입력한다.
7. PM이 AI 태스크 생성을 실행한다.
8. AI가 백로그를 만들고 별점 기반 담당자 추천을 계산한다.
9. PM이 추천안을 확정해 이슈를 만든다.
10. 스프린트를 만들고 이슈를 연결한다.
11. 팀원과 PM이 공유/개인 AI 채팅으로 다음 액션을 조정한다.

## 13. MVP 개발 우선순위
### 13.1 반드시 구현
- 회원가입/로그인
- 워크스페이스 생성
- 초대 링크 조회 및 참여
- 프로젝트 생성
- 프로젝트 참여 프로필 입력
- 팀원 목록
- AI 태스크 생성
- 별점 기반 업무 배정
- 백로그
- 스프린트/이슈 상태 관리
- AI PM 공유 채팅방

### 13.2 시간이 남으면
- 초대 링크 재발급/비활성화
- 개인 AI 채팅방
- 대시보드 고도화
- AI 회고
- 병목 감지 시각화
- 알림

### 13.3 제외
- 워크스페이스 목록
- 복잡한 조직 권한 관리
- 이메일 초대 발송
- 결제
- 다중 워크스페이스 전환

## 14. 발표용 소개 문장
- 기존 협업툴이 업무를 기록하는 도구라면, AI PM Workspace는 무엇을 해야 하고 누가 해야 하는지까지 AI가 제안하는 실행 중심 협업 도구다.
- PM이 없어도 프로젝트 설명과 팀원 프로필만 있으면 AI가 백로그를 만들고 적합한 담당자까지 추천한다.
- 사용자 역량을 계정에 고정하지 않고 프로젝트별 참여 프로필로 받기 때문에 해커톤처럼 역할이 자주 바뀌는 환경에 더 잘 맞는다.

## 15. MVP 시연 흐름
1. 방장이 워크스페이스를 생성한다.
2. 초대 링크를 복사한다.
3. 팀원이 초대 링크로 워크스페이스에 참여한다.
4. PM이 프로젝트를 생성한다.
5. 팀원이 프로젝트 참여 프로필을 입력한다.
6. PM이 AI 태스크 생성을 실행한다.
7. AI가 백로그를 생성한다.
8. AI가 별점 기반으로 담당자를 추천한다.
9. PM이 배정을 확정해 이슈를 만든다.
10. PM이 스프린트를 만들고 이슈를 연결한다.
11. 공유 AI 채팅에 “지금 가장 먼저 해야 할 일”을 묻고 추천 액션을 확인한다.
