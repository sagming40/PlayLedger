from rest_framework import viewsets, permissions

from .models import Entry
from .serializers import EntrySerializer


class EntryViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet 메서드 하나가 list/retrieve/create/update/partial_update/destroy
    6개 동작을 대신 해준다.
    RegisterView에서 사용했던 CreateAPIView의 '풀세트' 버전.
    """
    serializer_class = EntrySerializer
    
    # settings.py 전역 기본값이 IsAuthenticated이기 때문에 이 줄이 없어도
    # 이미 lock되어 있다. 그럼에도 명시적으로 다시 사용하는 이유:
    # "이 View는 login이 필요하다"라는 것을 이 파일만 보고도 알 수 있게 하기 위함.
    # 전역 설정에 의존하는 것과, 각 View가 스스로 선언하는 것은 안전성이 다르다.
    # 미래에 다른 누군가('나' 포함) settings.py를 잘못 건드려도 이 줄은 바뀌지 않는다. 
    permission_classes = [permissions.IsAuthenticated]
    
    # ── Playledger 프로젝트에서 가장 중요한 method ──
    # 사원증(permission_classes)은 login 여부만 확인한다.
    # login한 user가 "내 서랍"만 열 수 있게 막는 건 이 method의 역할이다.
    #
    # get_queryset을 사용하지 않고 queryset = Entry.objects.all() 라고만 작성해두면
    # login한 아무나 전체 user의 entries를 모두 열람할 수 있게 된다.
    # — 02_architecture.md에서 "이중으로 막는다"고 명시해 두었던 두 번째 자물쇠이다.
    def get_queryset(self):
        # self.request.user → token 인증을 통과하면 DRF가 자동으로 채워주는 값.
        # app이 "user_id=3 을 보여줘" 라고 요청할 방법 자체가 없다.
        # 오직 token이 누구 것이냐로만 결정된다.
        return Entry.objects.filter(user=self.request.user)
    
    
    # ── 생성 시점에 host를 못박는 method ──
    # Serializer.create()에서 validated_data["user"] 값이 여기서 채워진다.
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
