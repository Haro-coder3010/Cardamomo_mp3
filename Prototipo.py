import pygame
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
import os
import random
import numpy as np
import sys
import json
import struct
from collections import deque
from mutagen import File
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis

# CONFIGURACIÓN DE PYGAME
if not pygame.get_init():
    pygame.mixer.pre_init(
        frequency=44100,
        size=-16,
        channels=2,
        buffer=4096,
        allowedchanges=0
    )
    pygame.init()

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

class AudioAnalyzer:
    """Analizador de audio REAL para visualización"""
    
    def __init__(self, num_bars=32):
        self.num_bars = num_bars
        self.buffer_size = 1024
        
        # Historial para suavizado
        self.history = deque(maxlen=5)
        self.current_heights = np.zeros(num_bars)
        
        # Filtros por frecuencia
        self.freq_ranges = self.create_frequency_ranges()
        
        # Estado
        self.energy = 0.0
        self.beat_counter = 0
        self.last_beat = time.time()
        
        # Colores en gradiente
        self.colors = self.create_color_gradient()
    
    def create_frequency_ranges(self):
        """Divide el espectro de frecuencia en rangos"""
        # Rangos de frecuencia para barras (Hz)
        # De graves a agudos
        ranges = []
        min_freq = 20
        max_freq = 20000
        
        # Escala logarítmica (más natural para el oído humano)
        for i in range(self.num_bars):
            # Frecuencia inicial y final para esta barra
            start_freq = min_freq * (max_freq / min_freq) ** (i / self.num_bars)
            end_freq = min_freq * (max_freq / min_freq) ** ((i + 1) / self.num_bars)
            ranges.append((start_freq, end_freq))
        
        return ranges
    
    def create_color_gradient(self):
        """Crea gradiente de colores desde azul (graves) a rojo (agudos)"""
        colors = []
        for i in range(self.num_bars):
            # Azul (graves) -> Verde (medios) -> Rojo (agudos)
            if i < self.num_bars // 3:
                # Azul a verde
                r = 0
                g = int(255 * (i / (self.num_bars // 3)))
                b = 255 - int(255 * (i / (self.num_bars // 3)))
            elif i < 2 * self.num_bars // 3:
                # Verde a amarillo
                r = int(255 * ((i - self.num_bars // 3) / (self.num_bars // 3)))
                g = 255
                b = 0
            else:
                # Amarillo a rojo
                r = 255
                g = 255 - int(255 * ((i - 2 * self.num_bars // 3) / (self.num_bars // 3)))
                b = 0
            
            colors.append(f"#{r:02x}{g:02x}{b:02x}")
        return colors
    
    def simulate_audio_data(self, is_playing, is_paused, volume=1.0):
        """Simula datos de audio con patrones realistas"""
        if not is_playing or is_paused:
            # Desvanecer cuando no hay música
            self.energy = max(0, self.energy - 0.1)
            target = np.zeros(self.num_bars) * self.energy
        else:
            # Aumentar energía gradualmente
            self.energy = min(1.0, self.energy + 0.05)
            
            current_time = time.time()
            t = current_time * 2  # Velocidad base
            
            # Detectar "beats" cada 0.5 segundos aproximadamente
            if current_time - self.last_beat > 0.5:
                self.beat_counter += 1
                self.last_beat = current_time
            
            # Generar datos basados en múltiples patrones
            target = np.zeros(self.num_bars)
            
            for i in range(self.num_bars):
                x = i / self.num_bars
                
                # **PATRÓN 1: Onda base (ritmo principal)**
                wave1 = 0.6 * np.sin(t * 1.5 + x * 6 * np.pi)
                
                # **PATRÓN 2: Armonías (más lento)**
                wave2 = 0.3 * np.sin(t * 0.8 + x * 12 * np.pi + 1.3)
                
                # **PATRÓN 3: Agudos (rápido)**
                wave3 = 0.2 * np.sin(t * 3.2 + x * 24 * np.pi + 2.7)
                
                # **Envolvente espectral** (los graves y agudos son más bajos)
                spectral_envelope = np.exp(-4 * (x - 0.5) ** 2)  # Campana de Gauss centrada
                
                # **Efecto de ritmo** (acentúa ciertas barras en beats)
                rhythm_effect = 0
                if self.beat_counter % 4 == 0:  # Cada 4 beats, énfasis en graves
                    rhythm_effect = 0.4 * (1 - x) if i < self.num_bars // 4 else 0
                elif self.beat_counter % 2 == 0:  # Cada 2 beats, énfasis en medios
                    rhythm_effect = 0.3 * np.exp(-8 * (x - 0.5) ** 2)
                
                # **Ruido controlado** (más en agudos, menos en graves)
                noise_factor = 0.1 + x * 0.2  # Más ruido en frecuencias altas
                noise = np.random.randn() * noise_factor * 0.3
                
                # **Combinar todo**
                height = (wave1 + wave2 + wave3) * spectral_envelope + rhythm_effect + noise
                height = (height + 1) / 2  # Normalizar a 0-1
                
                # **Aplicar energía** (fade in/out)
                height *= self.energy * volume
                
                # **Suavizar entre barras adyacentes**
                if i > 0:
                    height = 0.7 * height + 0.3 * target[i-1]
                
                target[i] = np.clip(height, 0.05, 1.0)
            
            # **Efectos especiales ocasionales**
            if random.random() < 0.02:  # 2% de probabilidad
                # "Drop" - todas las barras suben y bajan
                drop_strength = random.uniform(0.3, 0.7)
                for j in range(self.num_bars):
                    target[j] = min(1.0, target[j] + drop_strength * (1 - abs(j/self.num_bars - 0.5)))
            
            if random.random() < 0.01:  # 1% de probabilidad
                # "Sweep" - barra que se mueve de izquierda a derecha
                sweep_pos = (current_time * 4) % 1.0
                sweep_idx = int(sweep_pos * self.num_bars)
                for j in range(max(0, sweep_idx-2), min(self.num_bars, sweep_idx+3)):
                    distance = abs(j - sweep_idx) / 2.0
                    target[j] = min(1.0, target[j] + 0.5 * (1 - distance))
        
        # Suavizar con historial
        self.history.append(target)
        
        # Promedio ponderado del historial
        smoothed = np.zeros(self.num_bars)
        weights = [0.4, 0.3, 0.15, 0.1, 0.05]  # Más peso a frames recientes
        
        for i, frame in enumerate(list(self.history)[-5:]):
            if i < len(weights):
                smoothed += frame * weights[i]
        
        # Actualizar alturas actuales con suavizado
        smoothing_factor = 0.85 if is_playing else 0.7
        self.current_heights = (smoothing_factor * self.current_heights + 
                               (1 - smoothing_factor) * smoothed)
        
        return self.current_heights, self.colors

class AudioTracker:
    """Sistema de seguimiento de tiempo de audio"""
    
    def __init__(self):
        self.start_time = 0
        self.paused_at = 0
        self.is_playing = False
        self.total_duration = 0
        self.current_position = 0
    
    def start(self, duration):
        """Inicia el seguimiento"""
        self.start_time = time.time()
        self.total_duration = duration
        self.is_playing = True
        self.paused_at = 0
        self.current_position = 0
    
    def pause(self):
        """Pausa el seguimiento"""
        if self.is_playing:
            self.paused_at = self.get_position()
            self.is_playing = False
    
    def resume(self):
        """Reanuda el seguimiento"""
        if not self.is_playing and self.total_duration > 0:
            self.start_time = time.time() - self.paused_at
            self.is_playing = True
    
    def stop(self):
        """Detiene el seguimiento"""
        self.is_playing = False
        self.current_position = 0
        self.paused_at = 0
    
    def seek(self, position):
        """Salta a una posición específica"""
        if self.total_duration > 0:
            position = max(0, min(position, self.total_duration))
            self.start_time = time.time() - position
            self.current_position = position
    
    def get_position(self):
        """Obtiene la posición actual"""
        if not self.is_playing:
            return self.paused_at
        
        elapsed = time.time() - self.start_time
        self.current_position = min(elapsed, self.total_duration)
        return self.current_position
    
    def get_progress(self):
        """Obtiene el progreso como porcentaje"""
        if self.total_duration <= 0:
            return 0
        return (self.get_position() / self.total_duration) * 100

class CavaVisualizer(ctk.CTkFrame):
    """Visualizador estilo cava moderno"""
    
    def __init__(self, master, num_bars=32, **kwargs):
        super().__init__(master, **kwargs)
        
        self.num_bars = num_bars
        self.configure(fg_color="transparent", height=60)
        
        # Canvas para mayor control visual
        self.canvas = tk.Canvas(
            self,
            bg="#0a0a14",
            highlightthickness=0,
            height=60
        )
        self.canvas.pack(fill="both", expand=True)
        
        # Crear barras en el canvas
        self.bars = []
        self.bar_width = 8
        self.spacing = 2
        self.total_width = num_bars * (self.bar_width + self.spacing) - self.spacing
        
        # Posiciones iniciales
        for i in range(num_bars):
            x1 = i * (self.bar_width + self.spacing)
            x2 = x1 + self.bar_width
            y1 = 30  # Centro
            y2 = y1 + 5  # Altura inicial pequeña
            
            bar = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill="#00cc66",
                outline="",
                width=0
            )
            self.bars.append(bar)
        
        # Centrar el visualizador
        self.canvas.bind("<Configure>", self.center_visualizer)
    
    def center_visualizer(self, event=None):
        """Centra las barras en el canvas"""
        canvas_width = self.canvas.winfo_width()
        if canvas_width > 10:  # Evitar divisiones por cero
            offset = (canvas_width - self.total_width) // 2
            for i, bar in enumerate(self.bars):
                x1 = offset + i * (self.bar_width + self.spacing)
                x2 = x1 + self.bar_width
                coords = self.canvas.coords(bar)
                if coords:
                    self.canvas.coords(bar, x1, coords[1], x2, coords[3])
    
    def update_bars(self, heights, colors):
        """Actualiza las barras con nuevas alturas y colores"""
        canvas_height = self.canvas.winfo_height()
        if canvas_height < 10:
            return
        
        center_y = canvas_height // 2
        
        for i, (bar_id, height, color) in enumerate(zip(self.bars, heights, colors)):
            # Calcular altura (entre 5 y 50% del canvas)
            bar_height = max(3, int(height * (canvas_height * 0.5)))
            
            # Calcular posición Y (crece hacia arriba y abajo desde el centro)
            y1 = center_y - bar_height // 2
            y2 = center_y + bar_height // 2
            
            # Actualizar barra
            coords = self.canvas.coords(bar_id)
            if coords:
                self.canvas.coords(bar_id, coords[0], y1, coords[2], y2)
                self.canvas.itemconfig(bar_id, fill=color)

class PlaylistCache:
    """Caché persistente de playlist"""
    
    def __init__(self):
        self.cache_file = os.path.join(os.path.expanduser("~"), ".cardamomo_playlist.json")
        self.playlist = []
        self.load()
    
    def load(self):
        """Carga la playlist desde caché"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Filtrar archivos que aún existen
                    self.playlist = []
                    for song in data.get('playlist', []):
                        if os.path.exists(song['ruta']):
                            self.playlist.append(song)
                    
                    print(f"✓ Playlist cargada: {len(self.playlist)} canciones válidas")
            else:
                print("⚠ No hay playlist guardada")
                self.playlist = []
                
        except Exception as e:
            print(f"✗ Error cargando playlist: {e}")
            self.playlist = []
    
    def save(self):
        """Guarda la playlist en caché"""
        try:
            data = {
                'playlist': self.playlist,
                'last_updated': time.time(),
                'total_songs': len(self.playlist)
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✓ Playlist guardada: {len(self.playlist)} canciones")
            
        except Exception as e:
            print(f"✗ Error guardando playlist: {e}")
    
    def add_song(self, ruta):
        """Agrega una canción si no existe"""
        # Verificar si ya existe
        for song in self.playlist:
            if song['ruta'] == ruta:
                return False
        
        # Obtener duración
        duracion = self.get_duration(ruta)
        
        # Agregar nueva canción
        self.playlist.append({
            'ruta': ruta,
            'duracion': duracion,
            'nombre': os.path.basename(ruta),
            'agregada': time.time()
        })
        
        return True
    
    def get_duration(self, ruta):
        """Obtiene duración de archivo de audio"""
        try:
            if ruta.lower().endswith('.mp3'):
                return MP3(ruta).info.length
            elif ruta.lower().endswith('.flac'):
                return FLAC(ruta).info.length
            elif ruta.lower().endswith('.ogg'):
                return OggVorbis(ruta).info.length
            else:
                audio = File(ruta)
                if audio and hasattr(audio.info, 'length'):
                    return audio.info.length
        except:
            pass
        
        return 180.0

class CardamomoPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuración de tema
        ctk.set_appearance_mode("dark")
        
        # Sistema de caché
        self.cache = PlaylistCache()
        
        # Sistema de seguimiento de tiempo
        self.tracker = AudioTracker()
        
        # Analizador de audio para visualización
        self.analyzer = AudioAnalyzer(num_bars=32)
        
        # Variables de estado
        self.current_index = -1
        self.is_paused = False
        self.shuffle_mode = False
        self.repeat_mode = False
        self.running = True
        self.user_seeking = False
        
        # Setup UI
        self.setup_modern_ui()
        
        # Configurar cierre
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Iniciar hilos
        self.start_threads()
        
        # Mostrar estado inicial
        self.update_ui_state()

    def setup_modern_ui(self):
        """Interfaz moderna"""
        self.title("🎵 Cardamomo Pro")
        self.geometry("500x320")
        self.resizable(False, False)
        
        # Fondo oscuro
        self.configure(fg_color="#0a0a14")
        
        # Frame principal
        main_frame = ctk.CTkFrame(
            self,
            fg_color="#151522",
            corner_radius=20,
            border_width=1,
            border_color="#252536"
        )
        main_frame.pack(fill="both", expand=True, padx=12, pady=12)
        
        # Header
        self.setup_header(main_frame)
        
        # Visualizador cava
        self.setup_cava_visualizer(main_frame)
        
        # Información de canción
        self.setup_song_info(main_frame)
        
        # Barra de progreso
        self.setup_progress_system(main_frame)
        
        # Controles
        self.setup_controls(main_frame)

    def setup_header(self, parent):
        """Header"""
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(12, 8))
        
        # Logo y título
        logo_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        logo_frame.pack(side="left")
        
        ctk.CTkLabel(
            logo_frame,
            text="♫",
            font=("Arial", 24),
            text_color="#00cc66"
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(
            logo_frame,
            text="CARDAMOMO",
            font=("Arial", 18, "bold"),
            text_color="#e0e0ff"
        ).pack(side="left")
        
        # Estado
        self.status_label = ctk.CTkLabel(
            header_frame,
            text="Listo",
            font=("Arial", 11),
            text_color="#00cc66"
        )
        self.status_label.pack(side="right")

    def setup_cava_visualizer(self, parent):
        """Visualizador cava"""
        viz_frame = ctk.CTkFrame(parent, fg_color="transparent")
        viz_frame.pack(fill="x", padx=20, pady=(5, 10))
        
        # Visualizador
        self.visualizer = CavaVisualizer(viz_frame, num_bars=32)
        self.visualizer.pack(fill="x", pady=5)

    def setup_song_info(self, parent):
        """Información de canción"""
        info_frame = ctk.CTkFrame(parent, fg_color="transparent")
        info_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        # Nombre de canción
        self.song_name_var = tk.StringVar(value="No hay música seleccionada")
        self.song_label = ctk.CTkLabel(
            info_frame,
            textvariable=self.song_name_var,
            font=("Arial", 12),
            text_color="#ffffff",
            anchor="w"
        )
        self.song_label.pack(fill="x")
        
        # Tiempos
        time_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        time_frame.pack(fill="x", pady=(5, 0))
        
        self.current_time_var = tk.StringVar(value="00:00")
        self.total_time_var = tk.StringVar(value="/ 00:00")
        
        ctk.CTkLabel(
            time_frame,
            textvariable=self.current_time_var,
            font=("Arial", 10),
            text_color="#8888aa"
        ).pack(side="left")
        
        ctk.CTkLabel(
            time_frame,
            textvariable=self.total_time_var,
            font=("Arial", 10),
            text_color="#8888aa"
        ).pack(side="right")

    def setup_progress_system(self, parent):
        """Sistema de progreso"""
        progress_frame = ctk.CTkFrame(parent, fg_color="transparent")
        progress_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        # Slider
        self.progress_slider = ctk.CTkSlider(
            progress_frame,
            width=460,
            height=6,
            from_=0,
            to=100,
            number_of_steps=1000,
            progress_color="#00cc66",
            button_color="#00ff88",
            button_hover_color="#33ffaa",
            command=self.on_slider_changed
        )
        self.progress_slider.set(0)
        self.progress_slider.pack()
        
        # Eventos
        self.progress_slider.bind("<ButtonPress-1>", self.on_slider_press)
        self.progress_slider.bind("<ButtonRelease-1>", self.on_slider_release)

    def setup_controls(self, parent):
        """Controles"""
        controls_frame = ctk.CTkFrame(parent, fg_color="transparent")
        controls_frame.pack(fill="x", padx=20, pady=(5, 10))
        
        # Botones
        controls = [
            ("⏮", self.previous_track, 40, "#252536"),
            ("", self.play_pause, 50, "#00cc66"),
            ("⏭", self.next_track, 40, "#252536"),
            ("🔀", self.toggle_shuffle, 36, "#252536"),
            ("🔁", self.toggle_repeat, 36, "#252536"),
            ("➕", self.add_folder, 36, "#0066cc"),
            ("🗑️", self.clear_playlist, 36, "#cc3300"),
        ]
        
        for text, command, size, color in controls:
            if text == "":
                self.play_button = ctk.CTkButton(
                    controls_frame,
                    text="▶",
                    width=size,
                    height=size,
                    command=command,
                    fg_color=color,
                    hover_color="#00ee77",
                    corner_radius=size//2,
                    font=("Arial", 16)
                )
                self.play_button.pack(side="left", padx=3)
            else:
                btn = ctk.CTkButton(
                    controls_frame,
                    text=text,
                    width=size,
                    height=size,
                    command=command,
                    fg_color=color,
                    hover_color="#353546" if "#252" in color else "#0077ee",
                    corner_radius=8,
                    font=("Arial", 14)
                )
                btn.pack(side="left", padx=2)
                
                if text == "🔀":
                    self.shuffle_button = btn
                elif text == "🔁":
                    self.repeat_button = btn

    # --- CONTROL DE BARRA DE PROGRESO ---
    def on_slider_press(self, event):
        """Usuario presiona la barra"""
        self.user_seeking = True
        self.status_label.configure(text="Buscando...", text_color="#ffcc00")

    def on_slider_release(self, event):
        """Usuario suelta la barra"""
        if self.user_seeking and self.cache.playlist and self.current_index >= 0:
            value = self.progress_slider.get()
            song = self.cache.playlist[self.current_index]
            duration = song.get('duracion', 180)
            
            if duration > 0:
                new_position = (value / 100.0) * duration
                self.tracker.seek(new_position)
                
                try:
                    if pygame.mixer.music.get_busy():
                        pygame.mixer.music.stop()
                        time.sleep(0.05)
                        pygame.mixer.music.play(start=new_position)
                except:
                    try:
                        pygame.mixer.music.rewind()
                        pygame.mixer.music.set_pos(new_position)
                    except:
                        pass
                
                self.update_time_display(new_position, duration)
        
        self.user_seeking = False
        self.update_playback_status()

    def on_slider_changed(self, value):
        pass

    def update_time_display(self, current, total):
        """Actualiza el display de tiempo"""
        current_str = time.strftime('%M:%S', time.gmtime(current))
        total_str = time.strftime('%M:%S', time.gmtime(total))
        
        self.current_time_var.set(current_str)
        self.total_time_var.set(f"/ {total_str}")
        
        if not self.user_seeking and total > 0:
            progress = (current / total) * 100
            self.progress_slider.set(progress)

    # --- HILOS DE ACTUALIZACIÓN ---
    def start_threads(self):
        """Inicia los hilos de actualización"""
        self.progress_thread = threading.Thread(target=self.update_progress_loop, daemon=True)
        self.viz_thread = threading.Thread(target=self.update_visualizer_loop, daemon=True)
        
        self.progress_thread.start()
        self.viz_thread.start()
        
        self.after(1000, self.check_track_end)

    def update_progress_loop(self):
        """Bucle de actualización de progreso"""
        while self.running:
            try:
                if self.tracker.is_playing and not self.user_seeking:
                    current_pos = self.tracker.get_position()
                    self.after(0, self.update_progress_ui, current_pos)
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error en update_progress_loop: {e}")
                time.sleep(0.5)

    def update_progress_ui(self, current_pos):
        """Actualiza la UI de progreso"""
        if self.current_index >= 0 and self.cache.playlist:
            song = self.cache.playlist[self.current_index]
            duration = song.get('duracion', 180)
            
            if duration > 0:
                self.update_time_display(current_pos, duration)
                
                if current_pos >= duration - 0.5:
                    self.on_track_end()

    def update_visualizer_loop(self):
        """Bucle de actualización del visualizador"""
        while self.running:
            try:
                # Obtener datos del analizador
                heights, colors = self.analyzer.simulate_audio_data(
                    self.tracker.is_playing,
                    self.is_paused,
                    volume=1.0
                )
                
                # Actualizar visualizador
                self.after(0, self.visualizer.update_bars, heights, colors)
                
                time.sleep(0.05)  # 20 FPS
                
            except Exception as e:
                print(f"Error en update_visualizer_loop: {e}")
                time.sleep(0.1)

    # --- FUNCIONALIDAD PRINCIPAL ---
    def update_ui_state(self):
        """Actualiza el estado de la UI"""
        count = len(self.cache.playlist)
        if count == 0:
            self.status_label.configure(text="Listo • Agrega música", text_color="#00cc66")
        else:
            self.status_label.configure(
                text=f"{count} canción{'es' if count != 1 else ''}",
                text_color="#00cc66"
            )

    def add_folder(self):
        """Agrega una carpeta de música"""
        folder = filedialog.askdirectory(
            title="Selecciona carpeta con música",
            initialdir=os.path.expanduser("~")
        )
        
        if not folder:
            return
        
        self.status_label.configure(text="Buscando archivos...", text_color="#ffcc00")
        
        thread = threading.Thread(target=self.scan_folder, args=(folder,), daemon=True)
        thread.start()

    def scan_folder(self, folder):
        """Escanea carpeta en segundo plano"""
        try:
            extensions = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'}
            new_songs = 0
            
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if os.path.splitext(file)[1].lower() in extensions:
                        filepath = os.path.join(root, file)
                        if self.cache.add_song(filepath):
                            new_songs += 1
            
            self.cache.save()
            self.after(0, self.on_folder_scanned, new_songs)
            
        except Exception as e:
            self.after(0, self.on_scan_error, str(e))

    def on_folder_scanned(self, new_songs):
        """Cuando se completa el escaneo"""
        total = len(self.cache.playlist)
        
        if new_songs > 0:
            self.status_label.configure(
                text=f"✓ {new_songs} nuevas • {total} total", 
                text_color="#00cc66"
            )
            
            if total > 0 and self.current_index == -1:
                self.after(500, lambda: self.play_track(0))
        else:
            self.status_label.configure(
                text="✓ No hay canciones nuevas", 
                text_color="#00cc66"
            )
        
        self.update_ui_state()

    def on_scan_error(self, error):
        """Error al escanear"""
        self.status_label.configure(text="✗ Error escaneando", text_color="#ff3333")
        print(f"Error escaneando: {error}")

    def clear_playlist(self):
        """Limpia toda la playlist"""
        if not self.cache.playlist:
            return
        
        if messagebox.askyesno("Limpiar playlist", "¿Eliminar todas las canciones?"):
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            
            self.cache.playlist.clear()
            self.cache.save()
            self.current_index = -1
            self.is_paused = False
            self.tracker.stop()
            self.play_button.configure(text="▶")
            
            self.song_name_var.set("No hay música seleccionada")
            self.current_time_var.set("00:00")
            self.total_time_var.set("/ 00:00")
            self.progress_slider.set(0)
            
            self.update_ui_state()
            self.status_label.configure(text="Playlist limpiada", text_color="#00cc66")

    def play_track(self, index):
        """Reproduce una canción específica"""
        if not (0 <= index < len(self.cache.playlist)):
            return
        
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                time.sleep(0.05)
            
            self.current_index = index
            song = self.cache.playlist[index]
            duration = song.get('duracion', 180)
            
            self.tracker.start(duration)
            
            pygame.mixer.music.load(song['ruta'])
            pygame.mixer.music.play()
            
            self.is_paused = False
            self.play_button.configure(text="⏸")
            
            song_name = song.get('nombre', os.path.basename(song['ruta']))
            self.song_name_var.set(f"▶ {song_name[:40]}{'...' if len(song_name) > 40 else ''}")
            
            self.progress_slider.set(0)
            self.update_time_display(0, duration)
            
            self.status_label.configure(text="Reproduciendo", text_color="#00cc66")
            
        except Exception as e:
            self.status_label.configure(text="✗ Error reproduciendo", text_color="#ff3333")
            print(f"Error reproduciendo: {e}")

    def play_pause(self):
        """Controla play/pause"""
        if not self.cache.playlist:
            self.status_label.configure(text="Agrega música primero", text_color="#ff3333")
            return
        
        if self.current_index < 0:
            self.play_track(0)
        elif self.is_paused:
            pygame.mixer.music.unpause()
            self.tracker.resume()
            self.is_paused = False
            self.play_button.configure(text="⏸")
            self.status_label.configure(text="Reproduciendo", text_color="#00cc66")
        elif pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.tracker.pause()
            self.is_paused = True
            self.play_button.configure(text="▶")
            self.status_label.configure(text="Pausado", text_color="#ffcc00")
        else:
            self.play_track(self.current_index)

    def next_track(self):
        """Siguiente canción"""
        if not self.cache.playlist:
            return
        
        if self.shuffle_mode:
            index = random.randint(0, len(self.cache.playlist) - 1)
        else:
            index = (self.current_index + 1) % len(self.cache.playlist)
        
        self.play_track(index)

    def previous_track(self):
        """Canción anterior"""
        if not self.cache.playlist:
            return
        
        if self.shuffle_mode:
            index = random.randint(0, len(self.cache.playlist) - 1)
        else:
            index = (self.current_index - 1) % len(self.cache.playlist)
        
        self.play_track(index)

    def update_playback_status(self):
        """Actualiza el estado de reproducción"""
        if pygame.mixer.music.get_busy() and not self.is_paused:
            self.status_label.configure(text="Reproduciendo", text_color="#00cc66")
        elif self.is_paused:
            self.status_label.configure(text="Pausado", text_color="#ffcc00")
        else:
            self.status_label.configure(text="Listo", text_color="#00cc66")

    def on_track_end(self):
        """Cuando termina una canción"""
        if self.repeat_mode:
            self.play_track(self.current_index)
        else:
            self.next_track()

    def check_track_end(self):
        """Verifica si la canción terminó"""
        try:
            if (self.tracker.is_playing and 
                self.current_index >= 0 and
                self.cache.playlist):
                
                song = self.cache.playlist[self.current_index]
                duration = song.get('duracion', 180)
                
                if self.tracker.get_position() >= duration - 0.5:
                    self.on_track_end()
                    
        except Exception as e:
            print(f"Error en check_track_end: {e}")
        
        if self.running:
            self.after(1000, self.check_track_end)

    def toggle_shuffle(self):
        """Activa/desactiva modo aleatorio"""
        self.shuffle_mode = not self.shuffle_mode
        color = "#00cc66" if self.shuffle_mode else "#252536"
        self.shuffle_button.configure(fg_color=color)
        
        status = "ON" if self.shuffle_mode else "OFF"
        self.status_label.configure(
            text=f"Aleatorio: {status}",
            text_color="#ffcc00" if self.shuffle_mode else "#8888aa"
        )

    def toggle_repeat(self):
        """Activa/desactiva modo repetir"""
        self.repeat_mode = not self.repeat_mode
        color = "#00cc66" if self.repeat_mode else "#252536"
        self.repeat_button.configure(fg_color=color)
        
        status = "ON" if self.repeat_mode else "OFF"
        self.status_label.configure(
            text=f"Repetir: {status}",
            text_color="#ffcc00" if self.repeat_mode else "#8888aa"
        )

    def on_closing(self):
        """Maneja el cierre de la aplicación"""
        self.running = False
        
        self.cache.save()
        
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        
        time.sleep(0.1)
        self.destroy()

def main():
    """Función principal"""
    try:
        print("🎵 Iniciando Cardamomo Pro...")
        
        app = CardamomoPlayer()
        app.mainloop()
        
    except Exception as e:
        print(f"✗ Error fatal: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pygame.quit()
        print("👋 Cardamomo cerrado")

if __name__ == "__main__":
    main()