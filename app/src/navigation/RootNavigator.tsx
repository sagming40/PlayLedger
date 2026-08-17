import React, { useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';

import LoginScreen from '../screens/LoginScreen';
import MainTabs from './MainTabs';

// TODO(M2): 지금은 로그인 여부를 가짜 state로 흉내만 냄
// 실제로는 app 시작 시 AsyncStorage에 저장된 Token이 있는지 확인 후 이 값을 정해야 함
// 04_ui_design.md 2장 "Token 유/무" 분기
function RootNavigator() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  
  return (
    // NavigationContainer는 모든 네비게이션의 최상위 포장지이다.
    // app 전체에서 딱 한 번만 존재해야 함
    <NavigationContainer>
      {isLoggedIn ? <MainTabs /> : <LoginScreen />}  
    </NavigationContainer>
  );
}

export default RootNavigator;
