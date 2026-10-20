/**
 * static/js/livekit-client.js
 * LiveKit WebRTC client manager, microphone controller, dual-channel mixer recording, and data channel receiver.
 */

const LiveKitManager = {
  room: null,
  audioElement: null,
  mediaRecorder: null,
  recordedChunks: [],
  audioCtx: null,
  destNode: null,
  sessionRoomName: null,

  async connect(url, token, handlers = {}, roomName = null) {
    const { onStatusChange, onTranscript, onDisconnect } = handlers;
    this.sessionRoomName = roomName;

    if (this.room) {
      await this.disconnect();
    }

    // Single dedicated hidden audio element for bot playback
    if (!this.audioElement) {
      this.audioElement = document.createElement("audio");
      this.audioElement.autoplay = true;
      document.body.appendChild(this.audioElement);
    }

    const RoomClass = window.LivekitClient ? window.LivekitClient.Room : null;
    if (!RoomClass) {
      throw new Error("LiveKit Web SDK not loaded. Check internet connection.");
    }

    this.room = new RoomClass({
      adaptiveStream: true,
      dynacast: true,
    });

    // 1. Connection state changes
    this.room.on(LivekitClient.RoomEvent.ConnectionStateChanged, (state) => {
      if (onStatusChange) onStatusChange(state);
    });

    // 2. Track Subscribed (Bot audio playback and mixer recording)
    this.room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {
      if (track.kind === LivekitClient.Track.Kind.Audio) {
        if (this.audioElement) {
          track.attach(this.audioElement);
        }
        this.addTrackToMixer(track);
        if (onStatusChange) onStatusChange("speaking");
      }
    });

    // 3. WebRTC Data Channel Receiver (Zero-polling real-time live chat + typing animation)
    this.room.on(LivekitClient.RoomEvent.DataReceived, (payload, participant) => {
      try {
        const textDecoder = new TextDecoder();
        const jsonStr = textDecoder.decode(payload);
        const data = JSON.parse(jsonStr);

        if (data.type === "typing") {
          if (window.LiveChat) {
            window.LiveChat.showTyping(data.speaker || "Alex");
          }
        } else if (data.type === "transcript") {
          if (window.LiveChat) {
            window.LiveChat.hideTyping();
          }
          if (onTranscript) {
            onTranscript(data.speaker, data.text, data.timestamp);
          }
        }
      } catch (err) {
        console.warn("Failed to parse data channel message:", err);
      }
    });

    // 4. Disconnect event
    this.room.on(LivekitClient.RoomEvent.Disconnected, () => {
      if (onDisconnect) onDisconnect();
    });

    // Connect to room
    await this.room.connect(url, token);

    // 5. Enable Local Microphone with Echo Cancellation and connect to call recorder
    try {
      await this.room.localParticipant.setMicrophoneEnabled(true, {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      });

      // Get local microphone track for mixer recording
      const pub = this.room.localParticipant.getTrackPublication(LivekitClient.Track.Source.Microphone);
      if (pub && pub.track) {
        this.addTrackToMixer(pub.track);
      }
    } catch (micErr) {
      console.warn("Microphone access prompt or device note:", micErr);
    }

    return this.room;
  },

  addTrackToMixer(track) {
    try {
      if (!this.audioCtx) {
        this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (this.audioCtx.state === "suspended") {
        this.audioCtx.resume();
      }
      if (!this.destNode) {
        this.destNode = this.audioCtx.createMediaStreamDestination();
      }

      const mediaStreamTrack = track.mediaStreamTrack || (track instanceof MediaStreamTrack ? track : null);
      if (mediaStreamTrack) {
        const stream = new MediaStream([mediaStreamTrack]);
        const source = this.audioCtx.createMediaStreamSource(stream);
        source.connect(this.destNode);
      }

      if (!this.mediaRecorder && this.destNode.stream.getAudioTracks().length > 0) {
        const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm";
        this.recordedChunks = [];
        this.mediaRecorder = new MediaRecorder(this.destNode.stream, { mimeType });
        this.mediaRecorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) {
            this.recordedChunks.push(e.data);
          }
        };
        this.mediaRecorder.start(500);
        console.log("Real call audio mixer recorder active.");
      }
    } catch (e) {
      console.warn("Error adding track to mixer recorder:", e);
    }
  },

  async stopAndUploadRecording(roomName) {
    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      return new Promise((resolve) => {
        this.mediaRecorder.onstop = async () => {
          try {
            if (this.recordedChunks.length > 0 && roomName) {
              const blob = new Blob(this.recordedChunks, { type: "audio/webm" });
              const formData = new FormData();
              formData.append("file", blob, `call_${roomName}.webm`);
              const resp = await fetch(`/api/calls/by-session/${roomName}/recording`, {
                method: "POST",
                body: formData
              });
              const resData = await resp.json();
              console.log("Real customer call recording uploaded successfully:", resData);
            }
          } catch (uploadErr) {
            console.warn("Failed to upload call recording:", uploadErr);
          }
          this.mediaRecorder = null;
          this.recordedChunks = [];
          resolve();
        };
        this.mediaRecorder.stop();
      });
    }
  },

  async disconnect() {
    const roomName = this.sessionRoomName;
    await this.stopAndUploadRecording(roomName);

    if (this.audioElement) {
      try {
        this.audioElement.pause();
        this.audioElement.srcObject = null;
      } catch (e) {}
    }

    if (this.audioCtx && this.audioCtx.state !== "closed") {
      try {
        await this.audioCtx.close();
      } catch (e) {}
      this.audioCtx = null;
      this.destNode = null;
    }

    if (this.room) {
      try {
        await this.room.disconnect();
      } catch (e) {
        console.error("Error during room disconnect:", e);
      }
      this.room = null;
    }

    this.sessionRoomName = null;
    if (window.LiveChat) {
      window.LiveChat.hideTyping();
    }
  }
};
