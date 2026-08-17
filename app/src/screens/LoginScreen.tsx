import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

// Login 화면 ─ Tap 구조 밖 (04_ui_design 네비게이션 구조 참고)
// token이 없을 때만 이 화면이 뜨는 흐름을 추후 RootNavigator에서 연결할 예정
function LoginScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>로그인 (준비 중)</Text>  
    </View>
  );  
}

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

export default LoginScreen;
