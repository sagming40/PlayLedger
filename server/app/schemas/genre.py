# app/schemas/genre.py
# 장르를 밖으로 내보낼 때의 모양 (응답 전용)

from pydantic import BaseModel, ConfigDict


class GenreRead(BaseModel):
    """장르 한 개의 응답 모양

    비유: 창고(DB) 물건에 붙이는 '진열용 라벨'
    물건에 적힌 정보 중 손님(화면)에게 필요한 것만 옮겨 적는다
    """

    # from_attributes ─ 객체의 속성(genre.id, genre.name)에서 값을 읽는다 (Dict ❌)
    # 이렇게 하지 않으면, SQLAlchemy 객체를 받았을 때 Pydanticdl 값을 꺼내지 못한다
    model_config = ConfigDict(from_attributes=True)

    id: int     # 등록 시에 이 값을 보내 장르를 고른다
    name: str   # chip에 표시할 글자

    # steam_genre_id는 넣지 않는다 ─ 화면이 사용할 일이 없는 값은 내보내지 않는다
    # UserRead에 password_hash가 없는 것과 같은 원칙. 비밀은 아니지만 필요가 없는건 내보내지 않는다
