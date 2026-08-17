from rest_framework import generics, permissions
from .serializers import RegisterSerializer

class RegisterView(generics.CreateAPIView):
    """
    회원가입 전용 API.
    CreateAPIView는 "POST를 받아서 생성만" 하는 상황에 맟춰진 미리 만들어진 View.
    request parsing → serialize 검증 → save() → 응답 조립까지 직접 짜야 하는 코드를
    DRF가 이 class 하나로 대신 해줌.
    """
    serializer_class = RegisterSerializer
    
    # ── "닭이 먼저냐, 달걀이 먼저냐" 문제를 푸는 지점 ──
    # → 로그인을 하려면 가입을 해야하는데, 가입을 하려면 로그인을 해야하는 상황
    # settings.py 전역 설정은 IsAuthenticated (기본 잠금)
    # 회원가입은 "아직 로그인을 하지 않은 사람"이 접근하는 것이 정상이므로,
    # 이 View 하나만 AllowAny로 예외를 뚫어줌.
    # "기본은 잠금, 예외만 개방" 원칙 ─ 이 줄이 예외 선언 자체이다.
    permission_classes = [permissions.AllowAny]
