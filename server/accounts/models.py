from django.contrib.auth.models import AbstractUser
from django.db import models

# AbstractUser = "기본 옵션 다 들어간 완성품 옷"
# username / password / email / is_staff / date_joined ... 이미 전부 들어있음
# 이 옷을 새로 재단하는 것이 아니라, 주머니 하나만 더 꿰매는 느낌
class User(AbstractUser):
    
    # AbstractUser의 email은 기본적으로 "중복 허용"임
    # ERD에서는 UNIQUE로 설정했으므로, 같은 이름의 필드를 다시 선언하여 덮어쓴다.
    # 덮어쓴다기 보다 "같은 자리에 다른 규격의 부품을 끼우는" 쪽에 더 가깝다.
    email = models.EmailField(
        "이메일",
        unique=True,
    )
    
    # M5에서 사용할 Steam 64비트 ID. 지금은 자리만 만들어 둔다.
    # null=True  → DB에 진짜 NULL이 들어가 수 있음 (연동을 하지 않은 경우)
    # blank=True → form/admin 화면에서 "비워둬도 통과"
    # 이 둘은 서로 다른 층위의 이야기라 항상 같이 다니진 않는다.
    steam_id = models.CharField(
        "Steam ID",
        max_length=20,
        null=True,
        blank=True,
        help_text="연동하지 않은 사용자는 비어 있음",
    )
    
    class Meta:
        # 이걸 사용하지 않으면 테이블 이름이 'accounts_user'가 된다.
        # ERD에 'users'라고 적어놓았으니 문서와 실물을 맞춰주는 것
        db_table = "users"
        verbose_name = "사용자"
        verbose_name_plural = "사용자"
    
    # 관리자 페이지나 shell에서 이 객체를 찍었을 때 뭘 보여줄지.
    # 이 과정이 없으면 <User: User object (1)> 라고만 떠서 누가 누군지 모름    
    def __str__(self):
        return self.username
    