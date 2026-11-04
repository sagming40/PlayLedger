// 상세에서 "라이브러리"로 돌아갈 때 보던 필터를 잃지 않게 마지막 목록 주소를 기억한다 (DESIGN 3.4절)
// 라우터가 적는 값만 들어온다 ─ 사용자 입력을 그대로 따라가지 않는다
const HOME = '/library'
let last = HOME

export function rememberLibrary(fullPath: string) {
  last = fullPath
}

export function libraryPath(): string {
  return last
}
