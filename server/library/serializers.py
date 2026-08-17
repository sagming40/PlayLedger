from rest_framework import serializers

from .models import Game, Genre, Entry
from .utils import normalize_title


# ============================================================
# 1. GenreSerializer — 장르 (read only)
# ============================================================
class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name"]


# ============================================================
# 2. GameSerializer — 게임 마스터 데이터
# ============================================================ 
# user가 직접 POST하는 대상이 아니다.
# Entry 응답 내에 "이 기록이 어떤 게임인지" 끼워 넣는 용도
class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ["id", "title", "steam_appid", "released_at"]
        # title_norm은 일부러 뺌. 기계가 사용하는 내부 값이기 때문에,
        # app에 내려줘봤자 사용할 곳이 없고, 오히려 "이게 뭔지" 헷갈리게 만든다. 
        

# ============================================================
# 3. EntrySerializer — 보유 기록 (Playledger 프로젝트의 핵심)
# ============================================================
class EntrySerializer(serializers.ModelSerializer):
    
    # ── read: 게임 정보를 통으로 끼워 넣는다 ──
    # entries 테이블엔 제목이 없다(game_id만 존재)
    # app이 목록 화면을 그리려면 제목이 필요한데, app에 게임마다
    # /games/3 을 또 호출하라고 지시하면 목록 20개 = 요청 21번이 된다.
    # 비유: 식당에서 밥을 시켰는데 반찬을 하나씩 따로 주문하게 하는 것
    # 따라서, server가 한 상에 차려서 내려준다.
    game = GameSerializer(read_only=True)
    
    # ── write: app이 보내는 값 ──
    # user는 game_id를 모른다. 등록 화면에서 입력하는 값은 "엘든 링"이라는 제목이다.
    # write_only=True → 요청으로 받기만 하고, 응답 JSON엔 실리지 않는다. (응답엔 위의 game 객체가 대신 나감)
    title = serializers.CharField(write_only=True, max_length=200)
    
    # M5 Steam 연동 때 사용할 자리. 현재 직접 등록에서는 거의 보내지 않지만,
    # 보낼 땐 중복 판별 1순위로 사용된다.
    steam_appid = serializers.IntegerField(
        write_only=True,
        required=False,
        allow_null=True,
    )              
    
    class Meta:
        model = Entry
        fields = [
            "id",
            "game",            # read_only (중첩)  
            "title",           # write_only
            "steam_appid",     # write_only
            "status",
            "purchased_at",
            "purchase_price",
            "playtime_hours",
            "rating",
            "review",
            "source",
            "updated_at",
        ]
        # ⭐ user is not in fields ⭐
        # 존재한다면 app이 "user: 3"이라고 보내서 남의 계정에 기록을 주입할 수 있다.
        # host는 app이 정하는 것이 아니라 token이 정한다. (View에서 주입)
        read_only_fields = ["id", "source", "updated_at"]
        

    # ── 개별 검증 필드 (검증 Method) ──
    # validate_<필드명> 이름 규칙을 지키면 DRF가 자동으로 호출한다.
    # 문지기가 방문객을 한 명씩 훑어보는 단계
    def validate_rating(self, value):
        if value is not None and not (1 <= value <= 5):
            raise serializers.ValidationError("평점은 1~5 사이여야 합니다.")
        return value

    def validate_playtime_hours(self, value):
        # playtime은 음수가 될 수 없다.
        # 이 부분을 걸러내지 않으면 M4 시간당 비용 계산에서 음수 값이 튀어나올 수 있다.
        if value is not None and value < 0:
            raise serializers.ValidationError("플레이타임은 0 이상이어야 합니다.")
        return value

    def validate_purchase_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("구매가는 0 이상이어야 합니다.")
        return value

    # ── 내부 헬퍼: 이 게임이 이미 game에 존재 하는지 ──
    # Python 관례 ─ 밑줄(_)로 시작하는 이름 → 내부용이므로 밖에서 호출하지 말 것.
    # 강제 ❌ , 권유 사항.
    def _resolve_game(self, title, steam_appid):
        """
        비유: 도서관 사서가 새 책 등록 요청을 받았을 때, 서가에 같은 책이 이미 존재한다면 
        새로운 청구기호를 생성하지 않고, 기존 청구기호를 알려주는 것.
    
        ERD 2.2절 '중복 판별 순서'를 그대로 코드로 옮긴 것.
        """ 
        # 1순위: steam_appid
        # Steam이 매긴 번호라 표기가 흔들릴 여지가 없다. 가장 신뢰할 만하다.
        if steam_appid is not None:
            game = Game.objects.filter(steam_appid=steam_appid).first()
            if game:
                return game
    
        # 2순위: title_norm
        # 표기를 세탁 라벨로 변환하여 비교
        norm = normalize_title(title)
        game = Game.objects.filter(title_norm=norm).first()
        if game:
            return game
    
        # 둘 다 못 찾았으면 진짜 새 게임 → games에 새 행 생성
        return Game.objects.create(
            title=title.strip(),   # 화면에 출력될 값은 사용가가 입력한 값 그대로
            title_norm=norm,       # 비교에 사용할 값은 정규화한 값
            steam_appid=steam_appid,
        )    

    def create(self, validated_data):
        # write_only 필드들은 Entry 모델에 존재하지 않는 컬럼이기 때문에 그대로 넘기면 에러가 발생한다.
        # pop()으로 꺼내는 동시에 삭제 — 소포에서 송장을 떼어내는 것
        title = validated_data.pop("title")
        steam_appid = validated_data.pop("steam_appid", None)
    
        # user는 View가 save(user=request.user)로 넣어준 값
        # app이 보낸 것이 아니라 token에서 나온 값이라는 점이 핵심
        user = validated_data["user"]
    
        game = self._resolve_game(title, steam_appid)
    
        # ── 같은 user가 같은 게임을 중복 등록하는 것을 차단 ──
        # DB에도 복합 UNIQUE(uq_user_game)가 걸려있지만 여기에서 한 번더 걸러내는 이유는
        # DB 까지 가서 걸리는 경우 IntegrityError가 터지고 → 500 응답이 나간다.
        # 500 응답은 "서버가 고장 났다"는 의미이다. user가 실수로 중복 입력한 것을
        # 서버 고장으로 알리면 안 된다. 400(잘못된 요청)이 올바른 응답이다.
        if Entry.objects.filter(user=user, game=game).exists():
            raise serializers.ValidationError(
                {"title": "이미 등록된 게임입니다."}
            )
    
        return Entry.objects.create(game=game, **validated_data)

    def update(self, instance, validated_data):
        # 수정은 '내 기록만' 고친다
        # 게임 제목은 games 테이블 = 전 user 공유 마스터 데이터이기 때문에,
        # 이 부분에서 수정을 하게 되면 나와 아무 상관 없는 다른 user의 화면 제목 까지 바뀌게 된다.
        # 비유: 아파트 공용 현관 도어락 비밀번호를 우리 집 도어락 비밀번호로 바꿔버리는 것.  
        #
        # 게임을 잘못 선택하여 등록한 경우 → 이 기록을 삭제한 후 다시 등록하는 것이 알맞다.
        validated_data.pop("title", None)
        validated_data.pop("steam_appid", None)
        return super().update(instance, validated_data)       
