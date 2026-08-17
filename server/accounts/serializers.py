from rest_framework import serializers
from django.contrib.auth import get_user_model

# AUTH_USER_MODEL 설정을 따라가서 실제 User 모델을 가져오는 함수
# "accounts.User"라고 직접 import하지 않고 우회하는 이유:
# 나중에 User 모델이 바뀌더라도 이 코드는 수정하지 않아도 됨 (설정 파일 하나만 보면 됨)
User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    # password 필드를 따로 선언하는 이유:
    # ModelSerializer가 자동으로 만드는 필드는 "그대로 보여주기"가 기본값이라
    # write_only 옵션을 주려면 이렇게 명시적으로 다시 써줘야함
    password = serializers.CharField(
        write_only=True,          # 받기만 하고, 응답 JSON엔 절대 싣지 않음
        min_length=8,             # 최소 길이는 여기서 1차로 막음 (서버 검증)
    )
    
    class Meta:
        model = User
        # 회원가입 때 받을 필드만 딱 지정
        # steam_id, is_staff 같은 필드는 여기 존재하지 않음. 만약, 사용자가 그 값을 넣더라도 무시됨 (보안)
        fields = ['id', 'username', 'email', 'password']
        # id는 응답으로는 보여주되(생성된 사용자 확인용), 입력으로는 받지 않음
        read_only_fields = ['id']
        
    def create(self, validated_data):
        # RegisterSerializer class의 핵심
        # validated_data는 검증을 통과한 Dictionary: {'username': ..., 'email': ..., 'password': '평문비번'}
        
        # ── User.objects.create()를 바로 사용하지 않는 이유 ──
        # create()는 넘긴 값을 그대로 저장함. password 필드에 평문을 입력하면
        # DB에 "1234abcd"가 그대로 저장됨 ─ 절대 금지
        # create_user()는 Django가 만들어준 전용 통로로, 내부에서
        # 자동으로 set_password()를 호출하여 hashing까지 한 번에 처리해준다.
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )     
        return user
