import sys
import subprocess

required = {'numpy','PySimpleGUI==4.18.1','opencv-contrib-python==4.5.3.56'}

for package in required:
  subprocess.call(['pip3','install',package])

requiredDll = {'libaec0', 'libaom0', 'libatk-bridge2.0-0', 'libatk1.0-0', 'libatlas3-base', 'libatspi2.0-0',\
 'libavcodec58', 'libavformat58', 'libavutil56', 'libbluray2', 'libcairo-gobject2', 'libcairo2',\
 'libchromaprint1', 'libcodec2-0.9', 'libdatrie1', 'libdav1d4', 'libdrm2', 'libepoxy0', 'libgdk-pixbuf-2.0-0',\
 'libgfortran5', 'libgme0', 'libgraphite2-3', 'libgsm1', 'libgtk-3-0', 'libharfbuzz0b', 'libhdf5-103-1',\
 'libilmbase25', 'libmp3lame0', 'libmpg123-0', 'libnorm1', 'libogg0', 'libopenexr25', 'libopenjp2-7',\
 'libopenmpt0', 'libopus0', 'libpango-1.0-0', 'libpangocairo-1.0-0', 'libpangoft2-1.0-0', 'libpgm-5.3-0',\
 'libpixman-1-0', 'librabbitmq4', 'librsvg2-2', 'libshine3', 'libsnappy1v5', 'libsodium23', 'libsoxr0',\
 'libspeex1', 'libsrt1.4-gnutls', 'libssh-gcrypt-4', 'libswresample3', 'libswscale5', 'libsz2', 'libthai0',\
 'libtheora0', 'libtwolame0', 'libudfread0', 'libva-drm2', 'libva-x11-2', 'libva2', 'libvdpau1', 'libvorbis0a',\
 'libvorbisenc2', 'libvorbisfile3', 'libvpx6', 'libwavpack1', 'libwayland-client0', 'libwayland-cursor0',\
 'libwayland-egl1', 'libwebpmux3', 'libx264-160', 'libx265-192', 'libxcb-render0', 'libxcb-shm0', 'libxcomposite1',\
 'libxcursor1', 'libxdamage1', 'libxfixes3', 'libxi6', 'libxinerama1', 'libxkbcommon0', 'libxrandr2',\
 'libxrender1', 'libxvidcore4', 'libzmq5', 'libzvbi0', 'ocl-icd-libopencl1'};

for driver in requiredDll:
  subprocess.call(['sudo','apt-get','install',driver])
