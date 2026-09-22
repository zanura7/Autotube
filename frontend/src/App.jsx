import { createSignal, onMount, onCleanup } from 'solid-js';

function App() {
  const [activeTab, setActiveTab] = createSignal("Dashboard");
  
  // Dashboard State
  const [urls, setUrls] = createSignal("");
  const [status, setStatus] = createSignal("Ready");
  const [progress, setProgress] = createSignal(0);

  // Live Stream State
  const [streamKey, setStreamKey] = createSignal("");
  const [videoPaths, setVideoPaths] = createSignal("");
  const [audioPath, setAudioPath] = createSignal("");
  const [liveStatus, setLiveStatus] = createSignal("Not Running");
  const [isScheduled, setIsScheduled] = createSignal(false);
  const [startTime, setStartTime] = createSignal("08:00");
  const [stopTime, setStopTime] = createSignal("17:00");
  const [isDraggingVideo, setIsDraggingVideo] = createSignal(false);
  const [isDraggingAudio, setIsDraggingAudio] = createSignal(false);

  // Generator State
  const [genMode, setGenMode] = createSignal("simple");
  const [genAudio, setGenAudio] = createSignal("");
  const [genBg, setGenBg] = createSignal("");
  const [genOut, setGenOut] = createSignal("output_video.mp4");
  const [genStyle, setGenStyle] = createSignal("Classic Bar");
  const [genImages, setGenImages] = createSignal([]);
  const [visBackgroundType, setVisBackgroundType] = createSignal("images");
  const [visAudioMode, setVisAudioMode] = createSignal("replace");
  const [visVideoShorter, setVisVideoShorter] = createSignal("loop");
  const [visImageOrder, setVisImageOrder] = createSignal("sequential");
  const [visImageDuration, setVisImageDuration] = createSignal(6);
  const [visTransition, setVisTransition] = createSignal("crossfade");
  const [visTransitionDuration, setVisTransitionDuration] = createSignal(0.8);
  const [visResolution, setVisResolution] = createSignal("1920x1080");
  const [visPosition, setVisPosition] = createSignal("bottom");
  const [visWidth, setVisWidth] = createSignal(1400);
  const [visHeight, setVisHeight] = createSignal(210);
  const [visBarCount, setVisBarCount] = createSignal(64);
  const [visSensitivity, setVisSensitivity] = createSignal(8);
  const [visOpacity, setVisOpacity] = createSignal(0.94);
  const [visPanelOpacity, setVisPanelOpacity] = createSignal(0.38);
  const [visColorOne, setVisColorOne] = createSignal("#c7ff2e");
  const [visColorTwo, setVisColorTwo] = createSignal("#ff654a");
  const [visMusicVolume, setVisMusicVolume] = createSignal(1);
  const [visOriginalVolume, setVisOriginalVolume] = createSignal(0.35);

  const [genBusy, setGenBusy] = createSignal(false);
  const [genStatus, setGenStatus] = createSignal("");
  const [genDownload, setGenDownload] = createSignal("");
  const [uploadCount, setUploadCount] = createSignal(0);
  let genPoll;
  let disposed = false;
  onCleanup(() => { disposed = true; clearTimeout(genPoll); });

  const readResponse = async (res) => {
    const data = await res.json();
    if (!res.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map(item => item.msg).join("; ")
        : data.detail;
      throw new Error(detail || `Request failed (${res.status})`);
    }
    return data;
  };

  const pollGeneration = async (id) => {
    try {
      const data = await readResponse(await fetch(`http://localhost:8000/api/v1/generator/${id}`));
      if (disposed) return;
      if (data.status === "Processing") {
        genPoll = setTimeout(() => pollGeneration(id), 1500);
        return;
      }
      setGenBusy(false);
      setGenStatus(data.status === "Completed" ? "Video ready." : "Generation failed. Check the server log for details.");
      if (data.status === "Completed") setGenDownload(`http://localhost:8000/api/v1/generator/${id}/download`);
      fetchProjects();
    } catch (error) {
      if (disposed) return;
      setGenStatus(`Unable to check render status: ${error.message}. Retrying...`);
      genPoll = setTimeout(() => pollGeneration(id), 3000);
    }
  };

  // History State
  const [projects, setProjects] = createSignal([]);

  const fetchProjects = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/history/");
      const data = await res.json();
      setProjects(data.projects);
    } catch(e) {
      console.error(e);
    }
  };

  onMount(() => {
    fetchProjects();
    const ws = new WebSocket("ws://localhost:8000/ws");
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "progress") {
        if (data.total > 0) setProgress(Math.round((data.current / data.total) * 100));
        if (data.text) {
          setStatus(data.text);
          setLiveStatus(data.text);
        }
      }
      if (data.type === "log" && data.level === "SUCCESS") {
         setLiveStatus("Live Stream Started!");
      }
    };
    onCleanup(() => { ws.onclose = null; ws.close(); });
    ws.onclose = () => {
      setStatus("Disconnected from server");
      setLiveStatus("Disconnected");
    };
  });

  const handleDownload = async () => {
    const urlList = urls().split('\n').filter(u => u.trim() !== "");
    if (urlList.length === 0) return;
    setStatus("Starting process...");
    setProgress(0);
    try {
      await fetch("http://localhost:8000/api/v1/downloader/batch", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ urls: urlList, format_type: "mp3_320", normalize: true })
      });
      setUrls("");
      setTimeout(fetchProjects, 1000);
    } catch (e) {
      setStatus("Error starting process.");
      console.error(e);
    }
  };

  const handleGenerate = async () => {
    if (genBusy() || uploadCount() > 0) return;
    const visualizer = genMode() === "visualizer";
    const visualReady = visualizer && visBackgroundType() === "images"
      ? genImages().length > 0
      : Boolean(genBg().trim());
    const audioRequired = genMode() !== "loop"
      && !(visualizer && visBackgroundType() === "video" && visAudioMode() === "keep");
    if (!genOut().trim() || !visualReady || (audioRequired && !genAudio().trim())) {
      setGenStatus("Select the required audio and visual sources and enter an output name.");
      return;
    }
    setGenBusy(true);
    setGenDownload("");
    setGenStatus("Starting generation...");
    try {
      const mixer = genMode() === "mixer";
      const data = await readResponse(await fetch("http://localhost:8000/api/v1/generator/start", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: genMode(),
          audio_path: mixer ? undefined : genAudio().trim() || null,
          bg_path: mixer ? undefined : genBg().trim(),
          output_name: genOut().trim(),
          style: genStyle(),
          image_folder: mixer ? genBg().trim() : undefined,
          audio_files: mixer ? genAudio().split('\n').map(p => p.trim()).filter(Boolean) : undefined,
          background_type: visualizer ? visBackgroundType() : undefined,
          image_files: visualizer && visBackgroundType() === "images" ? genImages() : undefined,
          audio_mode: visualizer ? visAudioMode() : undefined,
          video_shorter_mode: visualizer ? visVideoShorter() : undefined,
          image_order: visualizer ? visImageOrder() : undefined,
          image_duration: visualizer ? Number(visImageDuration()) : undefined,
          transition_type: visualizer ? visTransition() : undefined,
          transition_duration: visualizer ? Number(visTransitionDuration()) : undefined,
          resolution: visualizer ? visResolution() : undefined,
          visualizer_position: visualizer ? visPosition() : undefined,
          spectrum_width: visualizer ? Number(visWidth()) : undefined,
          spectrum_height: visualizer ? Number(visHeight()) : undefined,
          bar_count: visualizer ? Number(visBarCount()) : undefined,
          sensitivity: visualizer ? Number(visSensitivity()) : undefined,
          opacity: visualizer ? Number(visOpacity()) : undefined,
          panel_opacity: visualizer ? Number(visPanelOpacity()) : undefined,
          gradient_colors: visualizer ? [visColorOne(), visColorTwo()] : undefined,
          music_volume: visualizer ? Number(visMusicVolume()) : undefined,
          original_audio_volume: visualizer ? Number(visOriginalVolume()) : undefined
        })
      }));
      setGenStatus("Rendering video...");
      fetchProjects();
      pollGeneration(data.project_id);
    } catch(error) {
      setGenBusy(false);
      setGenStatus(error.message);
    }
  };

  const handleStartLive = async () => {
    if (!streamKey() || !videoPaths() || !audioPath()) return;
    
    try {
      const vPaths = videoPaths().split('\n').filter(p => p.trim() !== "");
      const streamData = { stream_key: streamKey(), video_paths: vPaths, audio_path: audioPath() };
      
      if (isScheduled()) {
        setLiveStatus(`Scheduled for ${startTime()} to ${stopTime()}`);
        await fetch("http://localhost:8000/api/v1/livestream/schedule", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            stream_data: streamData,
            start_time: startTime(),
            stop_time: stopTime()
          })
        });
      } else {
        setLiveStatus("Initializing stream...");
        await fetch("http://localhost:8000/api/v1/livestream/start", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(streamData)
        });
      }
    } catch(e) {
      setLiveStatus("Failed to start/schedule stream");
      console.error(e);
    }
  };

  const handleNewProject = () => {
    setActiveTab("Dashboard");
    setUrls("");
    setGenAudio("");
    setGenBg("");
    setGenImages([]);
    setGenOut("output_video.mp4");
    setStatus("Ready");
    setProgress(0);
  };

  const FileUpload = (props) => {
    const [isDragging, setIsDragging] = createSignal(false);
    const [uploading, setUploading] = createSignal(false);
    
    const handleFiles = async (fileList) => {
      const files = Array.from(fileList || []);
      if (files.length === 0) return;
      if (uploading()) return;
      if (props.multiple && files.length > 100) {
        setGenStatus("Select no more than 100 images.");
        return;
      }
      setUploading(true);
      setUploadCount(n => n + 1);
      try {
        const paths = [];
        for (const file of files) {
          const formData = new FormData();
          formData.append("file", file);
          const res = await fetch("http://localhost:8000/api/v1/generator/upload", {
            method: "POST",
            body: formData
          });
          const data = await readResponse(res);
          paths.push(data.path);
        }
        props.onUpload(props.multiple ? paths : paths[0]);
        setGenStatus("");
      } catch(e) {
        setGenStatus(`Upload failed: ${e.message}`);
      } finally {
        setUploadCount(n => n - 1);
        setUploading(false);
      }
    };

    const hasValue = () => Array.isArray(props.value) ? props.value.length > 0 : Boolean(props.value);
    const valueLabel = () => {
      if (Array.isArray(props.value)) {
        return props.value.length === 1
          ? props.value[0].split('/').pop()
          : `${props.value.length} images selected`;
      }
      return props.value ? props.value.split('/').pop() : "";
    };
  
    return (
      <div class="space-y-1.5">
        <label class="text-xs font-medium text-textMuted uppercase tracking-wider">{props.label}</label>
        <div 
          class={`border-2 border-dashed rounded-lg p-4 text-center transition-colors relative h-20 flex items-center justify-center group ${isDragging() ? 'border-primary bg-primary/10' : 'border-border bg-background hover:border-primary/50'}`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleFiles(e.dataTransfer.files); }}
        >
          <input 
            type="file" 
            class="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            onChange={async (e) => { await handleFiles(e.target.files); e.target.value = ""; }}
            accept={props.accept}
            multiple={props.multiple}
            disabled={props.disabled || uploading()}
            aria-label={props.label}
          />
          {uploading() ? (
            <span class="text-sm text-primary animate-pulse flex items-center gap-2">
              <div class="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
              Uploading...
            </span>
          ) : hasValue() ? (
            <div class="flex items-center gap-2 text-emerald-400">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
              <span class="text-sm font-mono truncate max-w-[240px]" title={valueLabel()}>{valueLabel()}</span>
            </div>
          ) : (
            <span class="text-sm text-textMuted group-hover:text-primary transition-colors">
              <span class="underline">Browse</span> or drag {props.multiple ? 'images' : 'a file'} here
            </span>
          )}
        </div>
      </div>
    );
  };

  return (
    <div class="flex min-h-screen w-full overflow-hidden selection:bg-primary/30">
      
      {/* Sidebar */}
      <aside class="hidden w-64 shrink-0 bg-surface border-r border-border p-6 md:flex md:flex-col">
        <div class="flex items-center gap-3 mb-10">
          <div class="bg-primary w-6 h-6 rounded flex items-center justify-center shadow-lg shadow-primary/20">
            <svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
          </div>
          <h1 class="text-xl font-semibold tracking-tight">Autotube</h1>
        </div>

        <nav class="flex flex-col gap-2">
          <button 
            onClick={() => setActiveTab("Dashboard")}
            class={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${activeTab() === "Dashboard" ? "bg-border text-textMain" : "text-textMuted hover:text-textMain hover:bg-border/50"}`}
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>
            Overview
          </button>
          
          <button 
            onClick={() => setActiveTab("Live Stream")}
            class={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${activeTab() === "Live Stream" ? "bg-border text-textMain" : "text-textMuted hover:text-textMain hover:bg-border/50"}`}
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            Live Stream
          </button>
        </nav>
      </aside>

      {/* Main Content */}
      <main class="min-w-0 flex-1 overflow-y-auto p-4 sm:p-6 lg:p-10">
        
        {/* Header */}
        <header class="flex justify-between items-center mb-6 lg:mb-10 max-w-5xl mx-auto">
          <h2 class="text-2xl font-semibold tracking-tight">{activeTab() === "Dashboard" ? "Dashboard" : "Live Stream"}</h2>
          <button 
            onClick={handleNewProject}
            class="bg-primary hover:bg-primaryHover text-white px-4 py-2 rounded-md text-sm font-medium transition-colors shadow-sm"
          >
            New Project
          </button>
        </header>

        <div class="max-w-5xl mx-auto space-y-6">
          
          {/* Dashboard View */}
          {activeTab() === "Dashboard" && (
            <>
              {/* Downloader Card */}
              <div class="bg-surface border border-border rounded-xl p-6 shadow-sm">
                <h3 class="text-lg font-medium mb-4">Process New Video</h3>
                
                <textarea 
                  rows="3" 
                  value={urls()}
                  onInput={(e) => setUrls(e.target.value)}
                  placeholder="Paste YouTube URLs here (one per line)..."
                  class="w-full bg-background border border-border rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50 transition-colors mb-4 resize-y font-mono"
                />
                
                <div class="flex justify-between items-center">
                  <div class="flex-1 mr-6">
                    <div class="flex justify-between text-xs text-textMuted mb-2">
                      <span class="truncate pr-4">{status()}</span>
                      {progress() > 0 && <span class="text-primary">{progress()}%</span>}
                    </div>
                    {progress() > 0 && (
                      <div class="w-full h-1.5 bg-background rounded-full overflow-hidden">
                        <div class="h-full bg-primary transition-all duration-300 ease-out rounded-full" style={{ width: `${progress()}%` }}></div>
                      </div>
                    )}
                  </div>
                  <button 
                    onClick={handleDownload}
                    class="bg-primary hover:bg-primaryHover text-white px-5 py-2.5 rounded-lg text-sm font-medium transition-colors shadow-sm whitespace-nowrap flex items-center gap-2"
                  >
                    Download 
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
                  </button>
                </div>
              </div>

              {/* Video Generator Card */}
              <div class="bg-surface border border-border rounded-xl p-6 shadow-sm">
                <h3 class="text-lg font-medium mb-5">Video Generator</h3>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
                  <div class="space-y-1.5">
                    <label class="text-xs font-medium text-textMuted uppercase tracking-wider">Mode</label>
                    <select 
                      disabled={genBusy() || uploadCount() > 0}
                      value={genMode()} 
                      onInput={e => { setGenMode(e.target.value); setGenAudio(""); setGenBg(""); setGenImages([]); }} 
                      class="w-full bg-background border border-border rounded-lg p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50"
                    >
                      <option value="simple">Simple Generator</option>
                      <option value="loop">Loop Creator</option>
                      <option value="visualizer">Audio Visualizer</option>
                      <option value="mixer">Playlist Creator (Mixer)</option>
                    </select>
                  </div>
                  
                  <div class="space-y-1.5">
                    <label class="text-xs font-medium text-textMuted uppercase tracking-wider">Output Name</label>
                    <input 
                      type="text" 
                      value={genOut()} 
                      onInput={e => setGenOut(e.target.value)} 
                      placeholder="output_video.mp4"
                      class="w-full bg-background border border-border rounded-lg p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50" 
                    />
                  </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
                  {genMode() === 'mixer' ? (
                    <>
                      <div class="space-y-1.5">
                        <label class="text-xs font-medium text-textMuted uppercase tracking-wider">Image Folder Path</label>
                        <input 
                          type="text" 
                          value={genBg()} 
                          onInput={e => setGenBg(e.target.value)} 
                          placeholder="/path/to/images_folder"
                          class="w-full bg-background border border-border rounded-lg p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50 font-mono" 
                        />
                      </div>
                      <div class="space-y-1.5">
                        <label class="text-xs font-medium text-textMuted uppercase tracking-wider">Audio Files (1 per line)</label>
                        <textarea 
                          rows="3"
                          value={genAudio()} 
                          onInput={e => setGenAudio(e.target.value)} 
                          placeholder="/path/to/audio1.mp3&#10;/path/to/audio2.mp3"
                          class="w-full bg-background border border-border rounded-lg p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50 font-mono resize-y" 
                        />
                      </div>
                    </>
                  ) : genMode() === 'visualizer' ? (
                    <>
                      <div class="space-y-1.5">
                        <label class="text-xs font-medium text-textMuted uppercase tracking-wider" for="vis-background-source">Background Source</label>
                        <select
                          id="vis-background-source"
                          disabled={genBusy() || uploadCount() > 0}
                          value={visBackgroundType()}
                          onInput={e => {
                            setVisBackgroundType(e.target.value);
                            setGenBg("");
                            setGenImages([]);
                            if (e.target.value === "images") setVisAudioMode("replace");
                          }}
                          class="w-full bg-background border border-border rounded-lg p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50"
                        >
                          <option value="images">Image Slideshow</option>
                          <option value="video">Video</option>
                        </select>
                      </div>
                      <FileUpload 
                        label={visBackgroundType() === "video" && visAudioMode() === "keep" ? "Music File (Not Used in Keep Mode)" : "Music File"}
                        accept="audio/*"
                        value={genAudio()}
                        onUpload={setGenAudio}
                        disabled={genBusy()}
                      />
                      {visBackgroundType() === "images" ? (
                        <FileUpload
                          label="Background Images (Up to 100)"
                          accept="image/*"
                          value={genImages()}
                          onUpload={setGenImages}
                          multiple={true}
                          disabled={genBusy()}
                        />
                      ) : (
                        <FileUpload
                          label="Background Video"
                          accept="video/*"
                          value={genBg()}
                          onUpload={setGenBg}
                          disabled={genBusy()}
                        />
                      )}
                      <div class="rounded-lg border border-border bg-background p-4 flex items-start gap-3">
                        <div class="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-emerald-400"></div>
                        <p class="text-xs leading-5 text-textMuted">
                          {visBackgroundType() === "images"
                            ? "Images play as a slideshow and repeat until the music ends."
                            : visAudioMode() === "replace"
                              ? "The original video audio is muted and replaced with the selected music."
                              : visAudioMode() === "mix"
                                ? "The original video audio is mixed with the selected music."
                                : "The visualizer follows the original audio from the video."}
                        </p>
                      </div>
                    </>
                  ) : (
                    <>
                      <FileUpload 
                        label="Audio Source"
                        accept="audio/*"
                        value={genAudio()}
                        onUpload={setGenAudio}
                        disabled={genBusy()}
                      />
                      <FileUpload 
                        label={genMode() === "loop" ? "Loop Video" : "Visual Source (Image or Video)"}
                        accept={genMode() === "loop" ? "video/*" : "image/*,video/*"}
                        value={genBg()}
                        onUpload={setGenBg}
                        disabled={genBusy()}
                      />
                    </>
                  )}
                </div>

                {genMode() === 'visualizer' && (
                  <div class="mb-5 rounded-xl border border-border bg-background/40 p-4">
                    <div class="mb-4 flex items-center justify-between gap-3">
                      <div>
                        <h4 class="text-sm font-semibold text-textMain">Media Settings</h4>
                        <p class="mt-1 text-xs text-textMuted">Control timing, audio behavior, and output frame.</p>
                      </div>
                      <span class="rounded bg-primary/15 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-indigo-300">
                        {visBackgroundType() === "images" ? `${genImages().length} images` : "video"}
                      </span>
                    </div>
                    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                      {visBackgroundType() === "video" ? (
                        <>
                          <div class="space-y-1.5">
                            <label class="text-xs font-medium text-textMuted" for="vis-audio-mode">Video Audio</label>
                            <select id="vis-audio-mode" value={visAudioMode()} onInput={e => setVisAudioMode(e.target.value)}
                              disabled={genBusy()} class="w-full rounded-lg border border-border bg-background p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50">
                              <option value="replace">Replace with music</option>
                              <option value="mix">Mix with music</option>
                              <option value="keep">Keep original audio</option>
                            </select>
                          </div>
                          <div class="space-y-1.5">
                            <label class="text-xs font-medium text-textMuted" for="vis-short-video">If Video Is Shorter</label>
                            <select id="vis-short-video" value={visVideoShorter()} onInput={e => setVisVideoShorter(e.target.value)}
                              disabled={genBusy()} class="w-full rounded-lg border border-border bg-background p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50">
                              <option value="loop">Loop video</option>
                              <option value="freeze">Hold final frame</option>
                            </select>
                          </div>
                          {visAudioMode() === "mix" && (
                            <>
                              <div class="space-y-1.5">
                                <label class="flex justify-between text-xs font-medium text-textMuted" for="vis-original-volume">
                                  <span>Original Volume</span><span>{Number(visOriginalVolume()).toFixed(2)}</span>
                                </label>
                                <input id="vis-original-volume" type="range" min="0" max="2" step="0.05" value={visOriginalVolume()}
                                  onInput={e => setVisOriginalVolume(e.target.value)} disabled={genBusy()} class="w-full accent-indigo-500" />
                              </div>
                              <div class="space-y-1.5">
                                <label class="flex justify-between text-xs font-medium text-textMuted" for="vis-music-volume">
                                  <span>Music Volume</span><span>{Number(visMusicVolume()).toFixed(2)}</span>
                                </label>
                                <input id="vis-music-volume" type="range" min="0" max="2" step="0.05" value={visMusicVolume()}
                                  onInput={e => setVisMusicVolume(e.target.value)} disabled={genBusy()} class="w-full accent-indigo-500" />
                              </div>
                            </>
                          )}
                        </>
                      ) : (
                        <>
                          <div class="space-y-1.5">
                            <label class="text-xs font-medium text-textMuted" for="vis-image-order">Image Order</label>
                            <select id="vis-image-order" value={visImageOrder()} onInput={e => setVisImageOrder(e.target.value)}
                              disabled={genBusy()} class="w-full rounded-lg border border-border bg-background p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50">
                              <option value="sequential">Sequential</option>
                              <option value="random">Random</option>
                            </select>
                          </div>
                          <div class="space-y-1.5">
                            <label class="text-xs font-medium text-textMuted" for="vis-image-duration">Seconds per Image</label>
                            <input id="vis-image-duration" type="number" min="0.5" max="120" step="0.5" value={visImageDuration()}
                              onInput={e => setVisImageDuration(e.target.value)} disabled={genBusy()}
                              class="w-full rounded-lg border border-border bg-background p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50" />
                          </div>
                          <div class="space-y-1.5">
                            <label class="text-xs font-medium text-textMuted" for="vis-transition">Transition</label>
                            <select id="vis-transition" value={visTransition()} onInput={e => setVisTransition(e.target.value)}
                              disabled={genBusy()} class="w-full rounded-lg border border-border bg-background p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50">
                              <option value="none">Cut</option>
                              <option value="fade">Fade through black</option>
                              <option value="crossfade">Crossfade</option>
                            </select>
                          </div>
                          {visTransition() !== "none" && (
                            <div class="space-y-1.5">
                              <label class="text-xs font-medium text-textMuted" for="vis-transition-duration">Transition Seconds</label>
                              <input id="vis-transition-duration" type="number" min="0.1" max="30" step="0.1" value={visTransitionDuration()}
                                onInput={e => setVisTransitionDuration(e.target.value)} disabled={genBusy()}
                                class="w-full rounded-lg border border-border bg-background p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50" />
                            </div>
                          )}
                        </>
                      )}
                      <div class="space-y-1.5">
                        <label class="text-xs font-medium text-textMuted" for="vis-resolution">Output Resolution</label>
                        <select id="vis-resolution" value={visResolution()} onInput={e => setVisResolution(e.target.value)}
                          disabled={genBusy()} class="w-full rounded-lg border border-border bg-background p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50">
                          <option value="1920x1080">1920 x 1080</option>
                          <option value="1280x720">1280 x 720</option>
                          <option value="1080x1920">1080 x 1920</option>
                          <option value="1080x1080">1080 x 1080</option>
                        </select>
                      </div>
                    </div>
                  </div>
                )}

                {genMode() === 'visualizer' && (
                  <div class="mb-6 rounded-xl border border-border bg-background/40 p-4">
                    <div class="mb-4">
                      <h4 class="text-sm font-semibold text-textMain">Visualizer Settings</h4>
                      <p class="mt-1 text-xs text-textMuted">Tune the spectrum layout and color treatment.</p>
                    </div>
                    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                      <div class="space-y-1.5">
                        <label class="text-xs font-medium text-textMuted" for="vis-style">Style</label>
                        <select id="vis-style" value={genStyle()} onInput={e => setGenStyle(e.target.value)}
                          disabled={genBusy()} class="w-full rounded-lg border border-border bg-background p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50">
                          <option value="Classic Bar">Classic Bar</option>
                          <option value="Rounded Bar">Rounded Bar</option>
                          <option value="Mirror Bar">Mirror Bar</option>
                          <option value="Fire">Fire Spectrum</option>
                          <option value="Smooth Wave">Smooth Wave</option>
                        </select>
                      </div>
                      <div class="space-y-1.5">
                        <label class="text-xs font-medium text-textMuted" for="vis-position">Position</label>
                        <select id="vis-position" value={visPosition()} onInput={e => setVisPosition(e.target.value)}
                          disabled={genBusy()} class="w-full rounded-lg border border-border bg-background p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50">
                          <option value="top">Top</option>
                          <option value="center">Center</option>
                          <option value="bottom">Bottom</option>
                        </select>
                      </div>
                      <div class="space-y-1.5">
                        <label class="text-xs font-medium text-textMuted" for="vis-width">Width</label>
                        <input id="vis-width" type="number" min="80" max="3840" step="10" value={visWidth()}
                          onInput={e => setVisWidth(e.target.value)} disabled={genBusy()}
                          class="w-full rounded-lg border border-border bg-background p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50" />
                      </div>
                      <div class="space-y-1.5">
                        <label class="text-xs font-medium text-textMuted" for="vis-height">Height</label>
                        <input id="vis-height" type="number" min="40" max="2160" step="10" value={visHeight()}
                          onInput={e => setVisHeight(e.target.value)} disabled={genBusy()}
                          class="w-full rounded-lg border border-border bg-background p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50" />
                      </div>
                      <div class="space-y-1.5">
                        <label class="text-xs font-medium text-textMuted" for="vis-bars">Bar Count</label>
                        <input id="vis-bars" type="number" min="8" max="256" step="1" value={visBarCount()}
                          onInput={e => setVisBarCount(e.target.value)} disabled={genBusy()}
                          class="w-full rounded-lg border border-border bg-background p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50" />
                      </div>
                      <div class="space-y-1.5">
                        <label class="flex justify-between text-xs font-medium text-textMuted" for="vis-sensitivity">
                          <span>Sensitivity</span><span>{Number(visSensitivity()).toFixed(1)}</span>
                        </label>
                        <input id="vis-sensitivity" type="range" min="0.1" max="12" step="0.1" value={visSensitivity()}
                          onInput={e => setVisSensitivity(e.target.value)} disabled={genBusy()} class="w-full accent-indigo-500" />
                      </div>
                      <div class="space-y-1.5">
                        <label class="flex justify-between text-xs font-medium text-textMuted" for="vis-opacity">
                          <span>Visualizer Opacity</span><span>{Math.round(Number(visOpacity()) * 100)}%</span>
                        </label>
                        <input id="vis-opacity" type="range" min="0.05" max="1" step="0.01" value={visOpacity()}
                          onInput={e => setVisOpacity(e.target.value)} disabled={genBusy()} class="w-full accent-indigo-500" />
                      </div>
                      <div class="space-y-1.5">
                        <label class="flex justify-between text-xs font-medium text-textMuted" for="vis-panel-opacity">
                          <span>Panel Opacity</span><span>{Math.round(Number(visPanelOpacity()) * 100)}%</span>
                        </label>
                        <input id="vis-panel-opacity" type="range" min="0" max="0.9" step="0.01" value={visPanelOpacity()}
                          onInput={e => setVisPanelOpacity(e.target.value)} disabled={genBusy()} class="w-full accent-indigo-500" />
                      </div>
                      <div class="space-y-1.5">
                        <label class="text-xs font-medium text-textMuted" for="vis-color-one">Primary Color</label>
                        <div class="flex items-center gap-2 rounded-lg border border-border bg-background p-2">
                          <input id="vis-color-one" type="color" value={visColorOne()} onInput={e => setVisColorOne(e.target.value)}
                            disabled={genBusy()} class="h-7 w-10 cursor-pointer rounded border-0 bg-transparent p-0" />
                          <span class="font-mono text-xs uppercase text-textMuted">{visColorOne()}</span>
                        </div>
                      </div>
                      <div class="space-y-1.5">
                        <label class="text-xs font-medium text-textMuted" for="vis-color-two">Secondary Color</label>
                        <div class="flex items-center gap-2 rounded-lg border border-border bg-background p-2">
                          <input id="vis-color-two" type="color" value={visColorTwo()} onInput={e => setVisColorTwo(e.target.value)}
                            disabled={genBusy()} class="h-7 w-10 cursor-pointer rounded border-0 bg-transparent p-0" />
                          <span class="font-mono text-xs uppercase text-textMuted">{visColorTwo()}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                
                <p class="text-sm text-textMuted mb-3" role="status" aria-live="polite">{genStatus()}</p>
                {genDownload() && <a class="text-sm text-emerald-400 underline" href={genDownload()}>Download generated video</a>}
                <div class="flex justify-end">
                  <button 
                    onClick={handleGenerate}
                    disabled={genBusy() || uploadCount() > 0}
                    class="bg-emerald-600 hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50 text-white px-5 py-2.5 rounded-lg text-sm font-medium transition-colors shadow-sm flex items-center gap-2"
                  >
                    {genBusy() ? "Rendering..." : uploadCount() > 0 ? "Uploading..." : "Generate Video"}
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                  </button>
                </div>
              </div>

              {/* Projects History */}
              <div class="pt-4">
                <h3 class="text-lg font-medium mb-4">Recent Projects</h3>
                
                {projects().length === 0 ? (
                  <div class="text-center py-12 border border-dashed border-border rounded-xl">
                    <p class="text-textMuted text-sm">No projects yet. Start by processing a video above.</p>
                  </div>
                ) : (
                  <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                    {projects().map(p => (
                      <div class="group bg-surface border border-border rounded-xl overflow-hidden hover:border-primary/50 transition-colors cursor-pointer">
                        <div class="aspect-video bg-background flex items-center justify-center text-border group-hover:text-primary/30 transition-colors relative">
                           <svg class="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                           {p.status === "Processing" && (
                             <div class="absolute inset-0 bg-background/50 flex items-center justify-center backdrop-blur-[1px]">
                               <div class="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                             </div>
                           )}
                        </div>
                        <div class="p-3">
                          <div class="text-sm font-medium text-textMain truncate mb-1" title={p.filename}>{p.filename}</div>
                          <div class="flex justify-between items-center">
                            <span class="text-xs text-textMuted">{p.project_type}</span>
                            <span class={`text-[10px] px-1.5 py-0.5 rounded-full ${p.status === 'Completed' ? 'bg-emerald-500/10 text-emerald-400' : p.status === 'Processing' ? 'bg-amber-500/10 text-amber-400' : 'bg-red-500/10 text-red-400'}`}>
                              {p.status}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

          {/* Live Stream View */}
          {activeTab() === "Live Stream" && (
            <div class="bg-surface border border-border rounded-xl p-6 shadow-sm max-w-3xl">
              <div class="flex items-center gap-3 mb-6">
                <div class="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse"></div>
                <h3 class="text-lg font-medium">Start 24/7 Live Stream</h3>
              </div>
              
              <div class="space-y-5 mb-8">
                <div class="space-y-1.5">
                  <label class="text-xs font-medium text-textMuted uppercase tracking-wider">YouTube RTMP Stream Key</label>
                  <input 
                    type="password"
                    value={streamKey()}
                    onInput={(e) => setStreamKey(e.target.value)}
                    placeholder="xxxx-xxxx-xxxx-xxxx-xxxx"
                    class="w-full bg-background border border-border rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50 font-mono tracking-widest"
                  />
                </div>

                <div class="space-y-1.5">
                  <div class="flex justify-between items-center">
                    <label class="text-xs font-medium text-textMuted uppercase tracking-wider">Video Sources (Absolute paths, 1 per line)</label>
                    <label class="text-xs font-medium text-primary hover:text-primaryHover cursor-pointer">
                      + Browse Files
                      <input type="file" multiple={true} accept="video/*" class="hidden" onChange={(e) => {
                        if (e.target.files && e.target.files.length > 0) {
                          const newPaths = Array.from(e.target.files).map(f => f.path || f.name).join('\n');
                          setVideoPaths(prev => prev ? prev + '\n' + newPaths : newPaths);
                        }
                        e.target.value = null;
                      }} />
                    </label>
                  </div>
                  <textarea 
                    rows="3" 
                    value={videoPaths()}
                    onInput={(e) => setVideoPaths(e.target.value)}
                    onDragOver={(e) => { e.preventDefault(); setIsDraggingVideo(true); }}
                    onDragLeave={() => setIsDraggingVideo(false)}
                    onDrop={(e) => {
                      e.preventDefault();
                      setIsDraggingVideo(false);
                      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                        const newPaths = Array.from(e.dataTransfer.files).map(f => f.path || f.name).join('\n');
                        setVideoPaths(prev => prev ? prev + '\n' + newPaths : newPaths);
                      }
                    }}
                    placeholder="Drag & Drop video files here...&#10;Or type absolute paths (1 per line)&#10;/home/user/videos/vid1.mp4"
                    class={`w-full bg-background border rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50 font-mono resize-y transition-colors ${isDraggingVideo() ? 'border-primary bg-primary/10 border-dashed' : 'border-border'}`}
                  />
                </div>

                <div class="space-y-1.5">
                  <div class="flex justify-between items-center">
                    <label class="text-xs font-medium text-textMuted uppercase tracking-wider">Audio Source (Absolute path)</label>
                    <label class="text-xs font-medium text-primary hover:text-primaryHover cursor-pointer">
                      + Browse File
                      <input type="file" accept="audio/*" class="hidden" onChange={(e) => {
                        if (e.target.files && e.target.files.length > 0) {
                          const file = e.target.files[0];
                          setAudioPath(file.path || file.name);
                        }
                        e.target.value = null;
                      }} />
                    </label>
                  </div>
                  <input 
                    type="text"
                    value={audioPath()}
                    onInput={(e) => setAudioPath(e.target.value)}
                    onDragOver={(e) => { e.preventDefault(); setIsDraggingAudio(true); }}
                    onDragLeave={() => setIsDraggingAudio(false)}
                    onDrop={(e) => {
                      e.preventDefault();
                      setIsDraggingAudio(false);
                      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                        const file = e.dataTransfer.files[0];
                        setAudioPath(file.path || file.name);
                      }
                    }}
                    placeholder="Drag & Drop audio file here... or type absolute path"
                    class={`w-full bg-background border rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50 font-mono transition-colors ${isDraggingAudio() ? 'border-primary bg-primary/10 border-dashed' : 'border-border'}`}
                  />
                </div>

                <div class="pt-4 border-t border-border/50">
                  <label class="flex items-center gap-3 cursor-pointer">
                    <input 
                      type="checkbox"
                      checked={isScheduled()}
                      onChange={(e) => setIsScheduled(e.target.checked)}
                      class="w-4 h-4 rounded border-border text-primary focus:ring-primary/50 bg-background"
                    />
                    <span class="text-sm font-medium">Enable Auto-Schedule (Daily)</span>
                  </label>
                  
                  {isScheduled() && (
                    <div class="grid grid-cols-2 gap-4 mt-4">
                      <div class="space-y-1.5">
                        <label class="text-xs font-medium text-textMuted uppercase tracking-wider">Start Time</label>
                        <input 
                          type="time"
                          value={startTime()}
                          onInput={(e) => setStartTime(e.target.value)}
                          class="w-full bg-background border border-border rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50"
                        />
                      </div>
                      <div class="space-y-1.5">
                        <label class="text-xs font-medium text-textMuted uppercase tracking-wider">Stop Time</label>
                        <input 
                          type="time"
                          value={stopTime()}
                          onInput={(e) => setStopTime(e.target.value)}
                          class="w-full bg-background border border-border rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50"
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
              
              <div class="flex justify-between items-center pt-4 border-t border-border">
                <div class="flex items-center gap-3">
                  <span class="text-sm text-textMuted">Status:</span>
                  <span class={`text-sm font-medium ${liveStatus().includes('Failed') ? 'text-red-400' : liveStatus().includes('Started') || liveStatus().includes('Scheduled') ? 'text-emerald-400' : 'text-primary'}`}>
                    {liveStatus()}
                  </span>
                </div>

                <button 
                  onClick={handleStartLive}
                  class={`${isScheduled() ? 'bg-primary hover:bg-primaryHover' : 'bg-red-600 hover:bg-red-700'} text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors shadow-sm flex items-center gap-2`}
                >
                  <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z"/></svg>
                  {isScheduled() ? "Schedule Live" : "Go Live"}
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
