from django.contrib import admin

from .models import Entry, Game, GameGenre, Genre


# 현재는 데이터가 하나도 없으므로 화려하게 꾸밀 필요 없이,
# "관리자 화면에만 출력되도록" 등록하여 직접 눈으로 확인 가능한 상태를 만든다.
admin.site.register(Game) 
admin.site.register(Genre) 
admin.site.register(GameGenre) 
admin.site.register(Entry) 
