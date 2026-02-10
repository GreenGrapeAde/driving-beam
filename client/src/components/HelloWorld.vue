<template>
  <div class="hello">
    <h2>Workspace</h2>
    <p>
      이 영역에 {{ mode }} 모드 화면을 구성!
      <br />
    </p>

    <div class="hint">
      <b>hmm..</b>
      <ul>
        <li>Live: MJPEG(/stream) & WebSocket(/ws) 연결</li>
        <li>Playback: 파일 선택/업로드 + 재생 제어</li>
        <li>A/B: slot=A/B 데이터로 화면 2줄 렌더링</li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
  name: "HelloWorld",
  props: {
    mode: {
      type: String,
      default: "live",
    },
  },
};
</script>
