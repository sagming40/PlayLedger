import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

import LibraryStack from './LibraryStack';
import StatsScreen from '../screens/StatsScreen';
import SettingsScreen from '../screens/SettingsScreen';

// 탭 관리자(자판기 본체) 하나를 만든다
// 이 시점엔 버튼이 몇 개인지, 뭘 보여줄지 아직 정해지지 않은 빈 뼈대이다.
const Tab = createBottomTabNavigator();

// 하단 탭 3개(라이브러리/통계/설정)를 이 곳에서 등록한다.
// 04_ui_design.md 2장 네비게이션 구조의 "하단 탭 네비게이션" 부분에 해당
function MainTabs() {
  return (
    <Tab.Navigator>
      <Tab.Screen
        name='Library'
        component={LibraryStack}
        options={{ title: '라이브러리', headerShown: false }}
      />
      <Tab.Screen
        name='Stats'
        component={StatsScreen}
        options={{ title: '통계' }}
      />
      <Tab.Screen
        name='Settings'
        component={SettingsScreen}
        options={{ title: '설정' }}
      />       
    </Tab.Navigator>
  );  
}

export default MainTabs;
