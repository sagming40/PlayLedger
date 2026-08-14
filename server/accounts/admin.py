from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


# UserAdmin을 그대로 사용하지 않고 상속하여 커스터마이징하는 이유:
# 기본 UserAdmin은 steam_id 필드를 알지 못하므로 화면에 보여주지 않는다.
# "이미 잘 만들어진 화면 틀 위에, 추가한 필드만 끼워 넣는" 방식.
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # UserAdmin.fieldsets는 편집 화면 섹션 구성을 Tuple로 define한 것.
    # 기존의 것을 그대로 사용하되(+ 연산), 마지막에 "Steam 연동" section 하나를 덧붙인다.
    fieldsets = UserAdmin.fieldsets + (
        ("Steam 연동", {"fields": ("steam_id",)}),
    )
    # 목록 화면(여러 사용자가 쭉 나열되는 화면)에 보일 컬럼들
    list_display = ("username", "email", "steam_id", "is_staff")
