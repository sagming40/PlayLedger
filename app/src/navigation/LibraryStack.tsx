import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import LibraryScreen from '../screens/LibraryScreen';

// 접시 쌓기 담당자 ─ 현재는 LibraryScreen 하나만 등록
// S-03(등록 폼)은 M2 후반, S-04(상세)는 M3에서 추가 예정 (Stack.Screen)
// 04_ui_design.md 2장: "라이브러리에서 진입해 뒤로가기로 돌아오는 스택 구조"에 해당
const Stack = createNativeStackNavigator();

function LibraryStack() {
  return (
    <Stack.Navigator>
      <Stack.Screen
        name='LibraryHome'
        component={LibraryScreen}
        options={{ title: '라이브러리' }}
      />    
    </Stack.Navigator>
  );  
}

export default LibraryStack;
