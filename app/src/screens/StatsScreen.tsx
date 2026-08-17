import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

function StatsScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>통계 (준비 중)</Text>  
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

export default StatsScreen;
