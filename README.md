`midi2gcode` 是一个把 MIDI 文件转换成 3D 打印机能够读取的 Gcode 开源软件。

使用效果展示：

- 《最伟大的作品》https://www.bilibili.com/video/BV1vd4y1M7er/
- 《歌剧魅影》https://youtu.be/L_MdsEhdfWM

它的主要特点是

- 支持同时使用打印机的 X 和 Y 轴
- 支持自定义打印机参数
- 支持 CoreXY 结构
- 支持多音轨的 MIDI 文件
- 全部使用 Python 实现，简单易懂

# 使用说明

1. 下载项目文件夹并解压缩
2. 根据自己的打印机参数，修改配置文件 `midi2gcode.config`。
   配置文件中默认设置为 **Voron 0.1** 3D 打印机。如果你的打印机参数设置与默认设置不同，那么生成的 Gcode 就有可能不能正常工作，甚至可能损坏打印机。所以请务必检查参数设置。
3. 把需要生成的 MIDI 文件复制到文件夹下，修改配置文件 `midi2gcode.config`中的`filename`的值，或者把 MIDI 文件重命名成默认值 `example.mid`
4. 双击运行 `midi2gcode.exe`
5. MIDI 文件就会被转换成多个 `.gcode`的文件，分别对应 MIDI 文件从的不同音轨，从高频率到低频率排列。通常高频率的音轨表现更好。
