from django.contrib import admin

from .models import Entry, Game, GameGenre, Genre
from .utils import normalize_title


# title_norm은 사람이 손으로 채우는 칸이 아니다.
# 이전 세션에서 admin 화면 자유 입력값 때문에 같은 게임이
# 두 번 생성됐던 문제(id 1, 2 발더스 게이트 3 중복)가 그 증거이다.
@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    readonly_fields = ["title_norm"]
    
    def save_model(self, request, obj, form, change):
        # 화면에서 못 건드리게만 막으면 빈 값으로 저장될 수 있다.
        # 따라서, 저장 직전에 title을 기준으로 server가 대신 계산해서 채운다.
        obj.title_norm = normalize_title(obj.title)
        super().save_model(request, obj, form, change) 


# 현재는 데이터가 하나도 없으므로 화려하게 꾸밀 필요 없이,
# "관리자 화면에만 출력되도록" 등록하여 직접 눈으로 확인 가능한 상태를 만든다.
#
# Genre, GameGenre, Entry는 아직 특별히 손볼 곳이 없어서
# 기본 admin 화면 그대로 등록만 해둔다. 
admin.site.register(Genre) 
admin.site.register(GameGenre) 
admin.site.register(Entry) 
