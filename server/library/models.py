from django.conf import settings
from django.db import models


# ============================================================
# 1. Game — 게임 자체 정보 (모든 사용자가 공유하는 마스터 데이터) 
# ============================================================
# 창고 비유: "상품 카탈로그" — User가 몇 명이든
# "사이버펑크 2077"이라는 카탈로그 항목은 딱 하나만 존재한다.
# 각 User가 "내가 이걸 구매했다"는 기록은 추후에 구현할 Entry에 따로 쌓인다.
class Game(models.Model):
    
    # 화면에 그대로 보여줄 제목. User가 입력한 그대로 저장
    title = models.CharField(
        "제목",
        max_length=200,
    )
    
    # 중복 판별 전용 필드. 사람이 보는 곳이 아니라 "기계가 비교를 하는 곳"
    # "사이버펑크 2077" / "Cyberpunk 2077" 처럼 표기가 달라도
    # 정규화(공백 제거·소문자 변환)를 거치면 같은 값이 될 수 있다.
    # 실제 정규화 로직(Python 함수)은 추후 Serializer/View 단계에서 작성한다.
    # — 지금은 "그 결과를 담을 자리"만 만들어 두는 것.
    title_norm = models.CharField(
        "정규화된 제목",
        max_length=200,
        db_index=True,  # ERD 4장 index 계획: 중복 판별 시 매번 조회되는 컬럼
    )
    
    # Steam 게임엔 고유 ID가 있음. 직접 입력한 게임은 이 값이 없을 수 있으므로 NULL 허용
    # unique=True + null=True 조합 → NULL은 여러 개가 있어도 걸리지 않고,
    # 실제 값이 들어간 것 끼리만 중복을 막아준다. (users.steam_id 때와 같은 원리)
    steam_appid = models.IntegerField(
        "Steam App ID",
        unique=True,
        null=True,
        blank=True,
    )
    
    released_at = models.DateField(
        "출시일",
        null=True,
        blank=True,
    )
    
    created_at = models.DateTimeField(
        "등록 시각",
        auto_now_add=True,
    )
    
    class Meta:
        db_table = "games"
        verbose_name = "게임"
        verbose_name_plural = "게임"
    
    def __str__(self):
        return self.title
    
    
# ============================================================
# 2. Genre — 장르 마스터
# ============================================================  
class Genre(models.Model):
    
    name = models.CharField(
        "장르명",
        max_length=50,
        unique=True,
    )
    
    class Meta:
        db_table = "genres"
        verbose_name = "장르"      
        verbose_name_plural = "장르"
    
    def __str__(self):
        return self.name 

# ============================================================
# 3. GameGenre — Game과 Genre를 잇는 연결 테이블 (N:M)
# ============================================================  
# 이 테이블이 별개로 필요한 이유:
# "게임 1개가 장르를 여러개 가질 수 있고, 장르 1개도 여러 게임에 걸쳐 있다"
# 이런 다대다(N:M) 관계는 두 테이블 간에 컬럼 하나만 추가하는 것 만으로는 표현할 수 없다.
# 따라서, "게임-장르 조합 1개 당 행 1개 씩"을 쌓는 중간 다리(연결 테이블)를 둔다.
#
# 참고: Django는 ManyToManyField 하나만 사용해도 이런 연결 테이블을 자동으로 생성해준다.
# 하지만 이 프로젝트에서는 수기로 작성한다. — ERD 문서에 game_genres라는 이름과 구조를 이미 명시해 두었고,
# "N:M이 실제로 어떻게 구현되는지"를 눈으로 직접 보고 이해하는 것이 이번 프로젝트의 학습 목적이기 때문
class GameGenre(models.Model):
    
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,   # 게임이 삭제되면 해당 연결도 같이 삭제 (고아 데이터 방지)
        db_column="game_id",
        verbose_name="게임",
    )
    genre = models.ForeignKey(
        Genre,
        on_delete=models.CASCADE,
        db_column="genre_id",
        verbose_name="장르",
    )           
    
    class Meta:
        db_table = "game_genres"
        verbose_name = "게임-장르 연결"
        verbose_name_plural = "게임-장르 연결"
        # 복합 UNIQUE: (game_id, genre_id) 조합이 이미 존재하는 경우 다시 넣지 못한다.
        # "엘든 링-액션"을 실수로 중복 입력 되는 것을 DB 단에서 막아주는 안전장치.
        constraints = [
            models.UniqueConstraint(
                fields=["game", "genre"],
                name="uq_game_genre",
            ),
        ]
        
    def __str__(self):
        return f"{self.game.title} - {self.genre.name}"  
    
    
# ============================================================
# 4. Entry — User의 "보유 기록" (이 project의 핵심 테이블)
# ============================================================  
class Entry(models.Model):
    
    # --- 상태값 선택지 ---
    # choices는 "이 field에 들어갈 수 있는 값의 화이트리스트"를 DB가 아니라
    # Python code에서 정의하는 방식이다. DB 컬럼 타입은 그냥 varchar지만,
    # Django가 "이 중 하나만 허용"이라는 검증을 App단에서 대신 해준다.
    #
    # Tuple의 첫 번째 값(BACKLOG)이 DB에 실제로 저장되는 값,
    # 두 번째 값("미시작")은 관리자 페이지 등에서 사람이 보는 표시용 텍스트.
    class Status(models.TextChoices):
        BACKLOG = "BACKLOG", "미시작"
        PLAYING = "PLAYING", "진행중"
        CLEARED = "CLEARED", "완료"
        ON_HOLD = "ON_HOLD", "보류"
        DROPPED = "DROPPED", "중단"
    
    # --- 출처 선택지 ---
    # 지금은 MANUAL(직접 입력)만 사용하지만, M5에서 STEAM이 추가될 것을 이미 인지하고 있으므로
    # choices 목록에 미리 정의해둔다. ERD 5장 "확장 여지"에 적힌 설계 그대로.
    class Source(models.TextChoices):
        MANUAL = "MANUAL", "직접 입력"
        STEAM = "STEAM", "Steam 동기화"
    
    # --- FK: 이 기록의 주인 ---
    # settings.AUTH_USER_MODEL을 사용하는 이유: 만약 accounts.User를 직접 import해서 사용하면,
    # 추후 User 모델을 변경하고 싶을 때 library 앱 코드까지 전부 고쳐야 한다.
    # 하지만 이런 식으로 "설정 값을 통해 간접 참조"를 하게 되면 accounts 쪽만 변경하고 이 쪽은 건드리지 않아도 된다.
    # (Django가 커스텀 User 모델을 참조할 때 공식적으로 권장하는 방식)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,   # 회원 탈퇴 시 그 사람의 보유 기록도 같이 정리
        db_column="user_id",
        related_name="entries",     # user.entries.all() 처럼 역방향 조회할 때 사용할 이름
        verbose_name="사용자",
    )            
    
    # --- FK: 무슨 게임인지 ---
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        db_column="game_id",
        related_name="entries",
        verbose_name="게임"
    )
    
    status = models.CharField(
        "상태",
        max_length=10,
        choices=Status.choices,
        default=Status.BACKLOG,
    )
    
    purchased_at = models.DateField(
        "구매일",
        null=True,
        blank=True,
    )
    
    purchase_price = models.IntegerField(
        "구매 가격",
        null=True,
        blank=True,
        help_text="원 단위",
    )
    
    playtime_hours = models.DecimalField(
        "플레이타임",
        max_digits=6,
        decimal_places=1,
        default=0,
        help_text="시간 단위. 소수점 첫째 자리까지",
    )
    
    # 평점은 CLEARED/DROPPED일 때만 입력한다는 규칙(04_ui_design.md 3.3)이 있지만,
    # 그 부분은 "화면/API 단에서 걸러줄 규칙"이므로 DB 컬럼 자체를 막을 이유는 아니다.
    # 따라서, 여기선 그냥 NULL 허용 정수로 두고, 검증은 추후 Serializer에서 담당.
    rating = models.PositiveSmallIntegerField(
        "평점",
        null=True,
        blank=True,
    )
    
    review = models.TextField(
        "한줄평",
        blank=True,  # blank=True만 존재하고 null=True는 없음 → 빈 문자열('')로 저장.
                     # 텍스트 필드는 "값이 아예 없음(NULL)"과 "빈 문자열"을 굳이
                     # 구분할 이유가 없어서 관례적으로 이런 식으로 표기함 (steam_id와 다른 판단)
    )
    
    source = models.CharField(
        "출처",
        max_length=10,
        choices=Source.choices,
        default=Source.MANUAL,
    )
    
    # auto_now=True → "저장할 때마다" 매번 현재 시각으로 자동 갱신
    # created_at(Game 모델)의 auto_now_add와 정반대 성격
    updated_at = models.DateTimeField(
        "수정 시각",
        auto_now=True,
    )
    
    class Meta:
        db_table = "entries"
        verbose_name = "보유 기록"
        verbose_name_plural = "보유 기록"
        constraints = [
            # ERD 4장에 명시된 그 제약: 한 사용자가 같은 게임을 중복 등록하지 못하도록
            # "내 라이브러리에 사이버펑크 2077을 두 줄로 중복 등록"을 DB가 원천 차단
            models.UniqueConstraint(
                fields=["user", "game"],
                name="uq_user_game",
            ),
        ]
        indexes = [
            # ERD 4장 인덱스 계획 그대로: 상태별 필터링이 가장 잦은 조회이므로
            # (user_id, status) 조합에 index를 걸어둔다.
            models.Index(fields=["user", "status"], name="idx_user_status"),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.game.title}"    
