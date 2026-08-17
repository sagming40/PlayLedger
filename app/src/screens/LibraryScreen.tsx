import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

// 화면 뼈대 ─ 실제 게임 목록은 API 연결 작업(M2 후반) 시 채워넣을 예정
// 화면을 Tab 했을 때 화면이 정상 출력 되는지만 확인 하는 용도
function LibraryScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>라이브러리 (준비 중)</Text>  
    </View>
  );  
}

// 비유: 자판기 안에서 물건 배치를 정해주듯,
// 화면 안 요소 들이 어디에 어떻게 놓일지 미리 정해두는 스타일 표
const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
  },  
});

export default LibraryScreen;
