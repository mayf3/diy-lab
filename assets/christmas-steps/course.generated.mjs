// GENERATED; edit source-data/christmas-magic-tent/workflow.json
export const COURSE = {
  "version": "1.0.0",
  "notice": "原创操作示意，不是真实录像；动作按官方资料与项目代码设计，尚未在你的硬件上验收。",
  "references": [
    {
      "id": "arduino-upload",
      "url": "https://support.arduino.cc/hc/en-us/articles/4733418441116-Upload-a-sketch-in-Arduino-IDE",
      "role": "Arduino 官方：安装开发板支持、打开程序与上传",
      "checked": "2026-11-10"
    },
    {
      "id": "arduino-board",
      "url": "https://support.arduino.cc/hc/en-us/articles/4406856349970-Select-board-and-port-in-Arduino-IDE",
      "role": "Arduino 官方：选择开发板与真实串口",
      "checked": "2026-11-10"
    },
    {
      "id": "arduino-input",
      "url": "https://docs.arduino.cc/built-in-examples/digital/InputPullupSerial/",
      "role": "Arduino 官方：D2 到 GND 的内部上拉按钮接法",
      "checked": "2026-11-10"
    },
    {
      "id": "arduino-power",
      "url": "https://docs.arduino.cc/learn/electronics/power-pins/",
      "role": "Arduino 官方：USB 供电与电源引脚边界",
      "checked": "2026-11-10"
    },
    {
      "id": "neopixel-best",
      "url": "https://learn.adafruit.com/adafruit-neopixel-uberguide/best-practices",
      "role": "Adafruit：DIN 串联电阻、并联电容、断电接线与共地",
      "checked": "2026-11-10"
    },
    {
      "id": "neopixel-power",
      "url": "https://learn.adafruit.com/adafruit-neopixel-uberguide/powering-neopixels/",
      "role": "Adafruit：小规模 USB 供电、极性与电流估算",
      "checked": "2026-11-10"
    }
  ],
  "lessons": [
    {
      "id": "blink",
      "action_ref": "A02",
      "number": "01",
      "title": "先让板上的小灯闪起来",
      "outcome": "证明电脑、数据线和旧 UNO 能一起工作。",
      "time": "按自己的速度操作",
      "materials": [
        "旧 UNO R3（ATmega328P）",
        "USB-A → USB-B 数据线",
        "Mac；只有 USB-C 时用 USB-C 公 → USB-A 母转接头"
      ],
      "prerequisite": "成人操作；干燥桌面。卸下全部外接线、盾板与外部电源。旧程序需要保留时先备份，再批准上传。",
      "refs": [
        "arduino-upload",
        "arduino-board",
        "arduino-power"
      ],
      "steps": [
        {
          "id": "b1",
          "title": "桌上只留下 UNO 和 USB 数据线",
          "scene": "parts",
          "do": "拔掉旧 UNO 上的全部外设和电源，放在不导电的桌垫上。",
          "expected": "板子只有 USB 插口等待接线；5V、VIN 和圆形电源口都空着。",
          "stop": "板子破损、松动或来源/型号不明时先停；不要接市电或打开充电头。",
          "check": "已确认是 UNO R3，全部外设已移开",
          "caption": "这一关只用旧 UNO，不接灯板、PIR 或喇叭。",
          "detail": "",
          "seconds": 10,
          "evidence_kind": "technical-schematic"
        },
        {
          "id": "b2",
          "title": "把方口 USB 插入 UNO",
          "scene": "usb",
          "do": "把 USB-B 方形插头插到 UNO 的 USB-B 插口；另一端接电脑。Mac 只有 USB-C 时按动画所示接转接头。",
          "expected": "板上的 ON 电源指示灯亮起；L 灯此时怎么闪不算本关成功。",
          "stop": "只亮灯却没有串口可能是充电线；不要用力硬插，也不要误接圆形电源口。",
          "check": "插头方向正确，ON 灯亮",
          "caption": "USB-B → UNO；USB-A → 转接头母口；USB-C 公头 → Mac。",
          "detail": "",
          "seconds": 10,
          "evidence_kind": "technical-schematic"
        },
        {
          "id": "b3",
          "title": "安装 IDE，选 Arduino Uno 与端口",
          "scene": "ideBoard",
          "do": "从 Arduino 官网安装 Arduino IDE。打开开发板管理器安装 Arduino AVR Boards，再在开发板选择器选择 Arduino Uno 和插线后新增的端口。",
          "expected": "选择器显示 Arduino Uno；端口是这块板插拔时出现/消失的那一项。",
          "stop": "不要选 UNO R4。没有新增端口就先换数据线/USB 口；克隆板驱动问题交给 Agent 按实际串口芯片核对，别装来历不明的驱动。",
          "check": "已选 Arduino Uno 和实际出现的端口",
          "caption": "IDE 界面为操作示意：先选板，再选真实端口。",
          "detail": "软件入口：https://www.arduino.cc/en/software/；不同 IDE 版本的界面位置可能不同。",
          "seconds": 13,
          "evidence_kind": "technical-schematic"
        },
        {
          "id": "b4",
          "title": "打开本关程序，点击向右的上传箭头",
          "scene": "ideUpload",
          "do": "下载下方 FirstBlink.ino，双击打开；IDE 提示建同名文件夹时同意。点击向右箭头「上传」，不要只点对勾「验证」。",
          "expected": "IDE 显示上传完成，而不是只有编译成功。",
          "stop": "上传失败先看板型、端口与数据线；不要更改 bootloader 或提高供电电压。",
          "check": "IDE 已显示上传完成",
          "caption": "上传把程序送到实物板子；对勾只检查代码。",
          "detail": "本关代码会替换板上旧程序。尚未准备好覆盖时停在这里。",
          "seconds": 13,
          "evidence_kind": "technical-schematic"
        },
        {
          "id": "b5",
          "title": "看 L 灯：亮一秒，灭一秒",
          "scene": "blink",
          "do": "找到板上标着 L 的小灯，连续观察三个亮灭周期。",
          "expected": "L 灯约每秒切换一次；ON 灯通常保持亮。",
          "stop": "不要把 ON 电源灯当成 L 灯。L 没按节奏闪时回到上一操作，检查程序是否真的上传。",
          "check": "实物 L 灯已连续完成三个亮灭周期",
          "caption": "这里展示的是预期节奏，不是读取你的板子。",
          "detail": "",
          "seconds": 10,
          "evidence_kind": "technical-schematic"
        }
      ],
      "files": [
        {
          "name": "FirstBlink.ino",
          "content": "// Maker Lab: lesson 1. UNO R3, built-in L LED only.\n// USB is the only power input; disconnect all external modules.\n#if !defined(ARDUINO_AVR_UNO)\n#error \"Choose Arduino Uno (UNO R3 / ATmega328P).\"\n#endif\nvoid setup() { pinMode(LED_BUILTIN, OUTPUT); }\nvoid loop() {\n  digitalWrite(LED_BUILTIN, HIGH); delay(1000);\n  digitalWrite(LED_BUILTIN, LOW); delay(1000);\n}\n"
        }
      ],
      "bundle_b64": "UEsDBBQAAAAIAAAAIQBnP7xf/wAAAGwBAAAZAAAARmlyc3RCbGluay9GaXJzdEJsaW5rLmlub32OsW7CMBRF93zFLSyJRBMoS1WmUKoSKRBE4zJGBr+AVWNHjtMWVfw7FmwMHd7ydM69N0mw4F9kkfPtCxS1rdEYxWDLAuvxANtOKvcoNXLkbzMYrU5xkCRgH1PIFu5A1x8a8+NDpG46N4GQ7c5oTTsHrhTo15HVXOFoROcr4qAvazwIqqUmEabrGcuWRZV+ritfGwV9stZY9F4PxrSE1IpOagPmL7ztQoK0PNKej5+eV1Hc84oWsg6+jRRoyXVNGOEPjdQLIyj0y6spy/IyWw5QsHLFymiC8w1XxlzpAH73XjquNla6O2mevc+9IkjxUzgaDofR5F8+Lzb3+Dm4AFBLAwQUAAAICAAAACEAx9JG49YAAAD1AAAAFwAAAFJFQURNRS3lvIDlp4vkuYvliY0udHh0Jc9RioJwEAbw9z1FN1ja7lEQ7H20EnQ1rbCgzKKlBbe1DKTWzOgw+c34f9or7EhvM/z4PmZoGdN0zpENb6cmJpJL473daXRbD61H7hfnd1hDGCbN9ig09k+Uj4ReaHYkyxaAvuA4bsJIKbxXtxvryV/h8OCMkSvwJlBmW+khx1KTgxgttae1xBAEkqCNo8JPOtlVMq3b8RGxfy2vRpnlcNcwA97mNPAkjctZhSv2IzJ/cVix9a12TpXoEoM3ZveIoocsq+f+/rVexin/2Bim8oLcX9f/A1BLAQIUAxQAAAAIAAAAIQBnP7xf/wAAAGwBAAAZAAAAAAAAAAAAAACAAQAAAABGaXJzdEJsaW5rL0ZpcnN0QmxpbmsuaW5vUEsBAhQDFAAACAgAAAAhAMfSRuPWAAAA9QAAABcAAAAAAAAAAAAAAIABNgEAAFJFQURNRS3lvIDlp4vkuYvliY0udHh0UEsFBgAAAAACAAIAjAAAAEECAAAAAA=="
    },
    {
      "id": "button",
      "action_ref": "A03",
      "number": "02",
      "title": "两根线，让按钮控制小灯",
      "outcome": "按住按钮 L 灯亮，松开后熄灭。暂时不用外接彩灯。",
      "time": "每接一根线停下来检查",
      "materials": [
        "已通过第 1 关的 UNO R3",
        "两端子常开、自复位按钮（如 R13-507）",
        "两根已可靠固定并绝缘的按钮引线；UNO 端为可插排母的公针"
      ],
      "prerequisite": "先完成第 1 关。面板按钮若只有裸焊片，先由会焊接的成人制成绝缘线束或选择已接线按钮；不要把裸线拧在焊片上。四脚轻触按钮不照搬本图。",
      "refs": [
        "arduino-input",
        "arduino-upload"
      ],
      "steps": [
        {
          "id": "k1",
          "title": "先拔掉 USB，再碰接线",
          "scene": "unplug",
          "do": "从 UNO 拔下 USB 线。确认没有外部电源接着它。",
          "expected": "ON 灯与 L 灯都熄灭。",
          "stop": "灯仍亮说明还在供电；先找到并断开电源，不能带电改线。",
          "check": "实物两盏指示灯均已熄灭",
          "caption": "先断电，后接线。",
          "detail": "",
          "seconds": 10,
          "evidence_kind": "technical-schematic"
        },
        {
          "id": "k2",
          "title": "把按钮的一根线接到 GND",
          "scene": "wireGround",
          "do": "找到 UNO 上丝印 GND，把按钮任一端子的引线插到这个 GND 孔。",
          "expected": "一根线连接按钮与 GND；另一根暂不接。",
          "stop": "以实物丝印为准，别数图上的孔位；不接 5V，不把裸线顶在孔边。",
          "check": "一根按钮线已牢固接到 GND",
          "caption": "按钮没有正负；先接 GND 这一根。",
          "detail": "",
          "seconds": 10,
          "evidence_kind": "technical-schematic"
        },
        {
          "id": "k3",
          "title": "把另一根线接到数字 2",
          "scene": "wireButton",
          "do": "找到数字引脚区标着 2 的孔，把按钮另一端的引线插进去。",
          "expected": "按钮的两个端子分别连 GND 和 D2，只有两根线。",
          "stop": "不要接模拟口 A2、TX/RX 或 5V。两端子之间不能被裸线永久短接。",
          "check": "另一根线接的是数字 2，不是 A2",
          "caption": "第二根线：按钮 → D2。",
          "detail": "",
          "seconds": 10,
          "evidence_kind": "technical-schematic"
        },
        {
          "id": "k4",
          "title": "核对两条连接，再接回 USB",
          "scene": "buttonCheck",
          "do": "沿两根线分别看一遍：一个端子到 GND、另一个到 D2。确认焊点绝缘且固定牢，再接回 USB。",
          "expected": "ON 灯重新亮起；程序尚未更新时按钮不必有反应。",
          "stop": "线头松动、铜丝外露或针脚挤在一起时先拔 USB 整理，不进入下一步。",
          "check": "两根线无松动、无裸露短路点",
          "caption": "复核：GND ↔ 按钮 ↔ D2。USB 是唯一电源。",
          "detail": "",
          "seconds": 10,
          "evidence_kind": "technical-schematic"
        },
        {
          "id": "k5",
          "title": "上传 ButtonLamp 程序",
          "scene": "ideButton",
          "do": "下载并打开 ButtonLamp.ino，仍选 Arduino Uno 和刚才的端口，点击上传箭头。",
          "expected": "上传完成。此时 L 灯在松开按钮时应该熄灭。",
          "stop": "程序里 INPUT_PULLUP 会启用内部上拉，不需要再接一根 5V 到按钮。",
          "check": "ButtonLamp 已上传完成",
          "caption": "这份程序读取 D2，用板载 L 灯显示按钮是否按下。",
          "detail": "",
          "seconds": 12,
          "evidence_kind": "technical-schematic"
        },
        {
          "id": "k6",
          "title": "按住、松开，重复三次",
          "scene": "buttonTest",
          "do": "按住实物按钮，观察 L 灯；松开再观察，重复三次。",
          "expected": "按住时 L 灯亮，松开约 30ms 后熄灭；不是按一下锁定开关。",
          "stop": "一直亮：检查按钮是否自锁、线是否短接。一直不亮：核对 D2/GND 和上传结果。先拔电再排查。",
          "check": "实物已完成三次“按亮、松灭”",
          "caption": "先看一次动画，再用你手里的按钮验证。",
          "detail": "",
          "seconds": 12,
          "evidence_kind": "technical-schematic"
        }
      ],
      "files": [
        {
          "name": "ButtonLamp.ino",
          "content": "// Maker Lab: lesson 2. A two-terminal normally-open momentary switch\n// connects D2 to GND. No 5V wire and no external resistor on the switch.\n// USB is the ONLY power input; disconnect USB before changing wires.\n#if !defined(ARDUINO_AVR_UNO)\n#error \"Choose Arduino Uno (UNO R3 / ATmega328P).\"\n#endif\nconstexpr unsigned char BUTTON_PIN = 2;\nbool previousRaw = false;\nbool stablePressed = false;\nunsigned long changedAt = 0;\nvoid setup() {\n  pinMode(BUTTON_PIN, INPUT_PULLUP);\n  pinMode(LED_BUILTIN, OUTPUT);\n  digitalWrite(LED_BUILTIN, LOW);\n}\nvoid loop() {\n  const unsigned long now = millis();\n  const bool pressed = digitalRead(BUTTON_PIN) == LOW;\n  if (pressed != previousRaw) {\n    previousRaw = pressed; changedAt = now;\n  }\n  if ((unsigned long)(now - changedAt) >= 30) stablePressed = pressed;\n  digitalWrite(LED_BUILTIN, stablePressed ? HIGH : LOW);\n  delay(2);\n}\n"
        }
      ],
      "bundle_b64": "UEsDBBQAAAAIAAAAIQC2lQ2I5QEAAGoDAAAZAAAAQnV0dG9uTGFtcC9CdXR0b25MYW1wLmlub32RQW/aQBCF7/4Vk+RiSwUiUKUqiFamVAmSY1vETtQTWvAAq653rN0lBFX57x0bk0Ai9bCX3Tffe/O214N78QcNRGJxAwqtJQ39LoTgdtRxaEqphQJNphRK7TtUoYaSStROmD3YnXTLjdfrwZK0xqWzMOmDI7iNJ12ICb4+wk4aBKELhgC+MLIGGrTSOjLAdm6DLahbk/KHMUjb3CZx9Bsq2nE+qautG0IhbevU6Ba4IqYvN0KvpV43XrbrXckVXBS4khoLP5xN8mmczMPH2TyPk8C7QmPY+fLnhsgihKbYSs6W8/FZALMB9CDMSlyLQf9bGnQveUQXcuWxtXX4UhnYaivXTK+tDYzzLEvieTqNYQT9obcgUlAZfJa0tTOx49uVUBbbF+vEQmHKUS0T3t7emIp4lWYnLELHguuh90yyAItuW/kB/PUAKqnvqUD/3fsLTOM0z+ZpHkV5GgxPRNGvyXycT6OsViV5xrLmvZBr6YR6MtJ9EEXJEyteD76K6GjbVADnUTXVG5ZSKWn9hntQHWto12zNZiiKk9QBjEa1Wz3G3+Yf9Rej0wYP5vCh1FY7PCuL09Ss15bnn2UN/Dps530ggO8jGFwHnz7lyP5vS+dDP+BuensHN215PIhK7P1+U+Q/UEsDBBQAAAgIAAAAIQDH0kbj1gAAAPUAAAAXAAAAUkVBRE1FLeW8gOWni+S5i+WJjS50eHQlz1GKgnAQBvD3PUU3WNruURDsfbQSdDWtsKDMoqUFt7UMpNbM6DD5zfh/2ivsSG8z/Pg+ZmgZ03TOkQ1vpyYmkkvjvd1pdFsPrUfuF+d3WEMYJs32KDT2T5SPhF5odiTLFoC+4DhuwkgpvFe3G+vJX+Hw4IyRK/AmUGZb6SHHUpODGC21p7XEEASSoI2jwk862VUyrdvxEbF/La9GmeVw1zAD3uY08CSNy1mFK/YjMn9xWLH1rXZOlegSgzdm94iihyyr5/7+tV7GKf/YGKbygtxf1/8DUEsBAhQDFAAAAAgAAAAhALaVDYjlAQAAagMAABkAAAAAAAAAAAAAAIABAAAAAEJ1dHRvbkxhbXAvQnV0dG9uTGFtcC5pbm9QSwECFAMUAAAICAAAACEAx9JG49YAAAD1AAAAFwAAAAAAAAAAAAAAgAEcAgAAUkVBRE1FLeW8gOWni+S5i+WJjS50eHRQSwUGAAAAAAIAAgCMAAAAJwMAAAAA"
    },
    {
      "id": "pixels",
      "action_ref": "A04",
      "number": "03",
      "title": "把小灯换成四颗彩灯",
      "outcome": "短按切换暖色 / 彩色 / 熄灭，长按关闭。",
      "time": "桌面测试，不接 PIR 和音频",
      "materials": [
        "前两关的 UNO、按钮与可靠线束",
        "一块只有 4 颗的 5V WS2812B 灯板（已预焊线/排针）",
        "330Ω 电阻 ×1",
        "1000µF / 10V 电解电容 ×1",
        "绝缘的可靠接点或面包板；已准备好的公针连接线"
      ],
      "prerequisite": "这是单独的低亮度桌面小实验，不是最终音频整机供电图。仅 UNO USB 单入口、4 颗灯、没有 DFPlayer/PIR/外部 5V。灯板端子顺序按实物 5V / DIN / GND 丝印，不能照图猜。未预焊或无可靠接点就先准备端子，不带电凑接。",
      "refs": [
        "neopixel-best",
        "neopixel-power",
        "arduino-power"
      ],
      "steps": [
        {
          "id": "p1",
          "title": "先装库并上传彩灯程序",
          "scene": "idePixels",
          "do": "在 Arduino IDE 的库管理器安装 Adafruit NeoPixel。下载代码包，打开 ChristmasStar 文件夹中的 .ino（controller.h 必须同目录），在灯板尚未接入时上传。",
          "expected": "编译和上传完成。仅有 UNO 和按钮时，不要求板载 L 灯继续响应。",
          "stop": "缺 Adafruit_NeoPixel.h 就检查库是否安装；缺 controller.h 就把两个文件放回同一文件夹。不要改成其他板型跳过检查。",
          "check": "ChristmasStar 已上传；两个源码文件在同一文件夹",
          "caption": "先上传，再断电接灯板。",
          "detail": "",
          "seconds": 14,
          "evidence_kind": "technical-schematic"
        },
        {
          "id": "p2",
          "title": "拔 USB，认清灯板输入端",
          "scene": "pixelParts",
          "do": "拔掉 USB，等指示灯熄灭。找到四灯板的 5V、DIN、GND 标记；把 DOUT 留空。",
          "expected": "灯板断电，输入 DIN 已辨认，灯珠总数只有 4。",
          "stop": "只有 12V 标记、灯珠更多或没有清楚丝印时停下；不要按焊盘左右位置猜。",
          "check": "已找到 5V / DIN / GND，确认不是 DOUT",
          "caption": "灯板外形可能不同：跟丝印，不跟示意图位置。",
          "detail": "",
          "seconds": 10,
          "evidence_kind": "technical-schematic"
        },
        {
          "id": "p3",
          "title": "先连接灯板 GND",
          "scene": "pixelGround",
          "do": "将灯板 GND 连接到 UNO 的 GND。按钮原来的 GND 也保留；需要分线时用可靠公共接点。",
          "expected": "灯板与 UNO 共地，仍未通电。",
          "stop": "不要把两个粗线头强塞进一个 UNO 插孔；缺分线接点就先准备。",
          "check": "灯板 GND 已可靠接回 UNO GND",
          "caption": "黑线表示 GND；标签比线色更重要。",
          "detail": "",
          "seconds": 10,
          "evidence_kind": "technical-schematic"
        },
        {
          "id": "p4",
          "title": "把 UNO 的 5V 输出接到灯板 5V",
          "scene": "pixelPower",
          "do": "在断电状态下，将 UNO 的 5V 输出连接到四灯板 5V。这里只从 UNO 给小灯板供电，不向 UNO 5V 口倒灌。",
          "expected": "5V 到 5V，GND 到 GND，两条电源线分开且没有短接。",
          "stop": "本关不连接充电头分线板；不要把整套灯光、音频都挂到这条小实验电源上。",
          "check": "已确认 5V 与 GND 没接反或短接",
          "caption": "USB → UNO → 4 颗低亮度 LED，仅本关的桌面基线。",
          "detail": "",
          "seconds": 10,
          "evidence_kind": "technical-schematic"
        },
        {
          "id": "p5",
          "title": "在灯板电源旁并联电容",
          "scene": "capacitor",
          "do": "电容正脚接灯板 5V，带负号条纹的一侧接 GND。接在同一对电源节点上，不是串在导线上。",
          "expected": "电容的 + 到 5V、− 到 GND，两个脚绝缘分开。",
          "stop": "长脚仅供未剪脚时辅助辨认，以电容极性标记为准。极性看不清、鼓包或破损就不用。",
          "check": "电容极性、额定电压和绝缘已核对",
          "caption": "1000µF / 10V：并联在 5V 与 GND 之间。",
          "detail": "",
          "seconds": 12,
          "evidence_kind": "technical-schematic"
        },
        {
          "id": "p6",
          "title": "D6 经过 330Ω 电阻再到 DIN",
          "scene": "pixelData",
          "do": "把 UNO 数字 6 接到 330Ω 电阻一端，电阻另一端接灯板 DIN。电阻尽量靠近灯板。",
          "expected": "数据线路是 D6 → 330Ω → DIN；不是 DOUT，也不是 5V。",
          "stop": "电阻没有正负，但要核对阻值；没有可靠固定点时不要扭接裸线。",
          "check": "数据线完整经过 330Ω 并到 DIN",
          "caption": "电阻在数据线上，不串在 5V 电源线上。",
          "detail": "",
          "seconds": 12,
          "evidence_kind": "technical-schematic"
        },
        {
          "id": "p7",
          "title": "最后检查，才插回 USB",
          "scene": "pixelCheck",
          "do": "核对 GND、5V、电容极性、D6→330Ω→DIN、D2 按钮五项；确认线路固定，才插回 USB。",
          "expected": "上电默认熄灯。没有冒烟、异味、异常发热或反复重启。",
          "stop": "出现异常立即拔 USB。USB 是唯一电源；不加声音模块，不靠提高电压解决问题。",
          "check": "五项核对完成，通电无异常且默认熄灯",
          "caption": "默认熄灯是设计行为，不是接线失败。",
          "detail": "",
          "seconds": 12,
          "evidence_kind": "technical-schematic"
        },
        {
          "id": "p8",
          "title": "短按换色，长按关闭",
          "scene": "pixelTest",
          "do": "短按并松开：暖色。再短按：彩色。第三次：熄灭。点亮后按住超过 1.2 秒，应直接关闭。",
          "expected": "四颗灯按顺序变化，长按关闭后松手不会再次点亮。",
          "stop": "灯不亮先拔电查 DIN/DOUT、共地和库配置；不要把亮度拉满来排错。颜色顺序异常先核对灯板类型。",
          "check": "实物已完成三次切换和一次长按关闭",
          "caption": "这就是小屋第一件独立可用的互动装置。",
          "detail": "",
          "seconds": 16,
          "evidence_kind": "technical-schematic"
        }
      ],
      "files": [
        {
          "name": "ChristmasStar.ino",
          "content": "/* ChristmasStar — tutorial baseline: confirmed UNO R3 / ATmega328P / 5V only.\n   D2 -> momentary NO button -> GND (INPUT_PULLUP)\n   D6 -> 330 ohm series resistor -> 5V WS2812B RGB DIN\n   5V/GND -> FOUR pixels maximum; 1000uF >=10V across their power input.\n   Single power entry through UNO USB. No external supply on 5V/VIN.\n   This sketch is not a hardware/electrical safety certification.\n*/\n#if !defined(ARDUINO_AVR_UNO)\n#error \"Select confirmed Arduino UNO R3 / ATmega328P; do not reuse this wiring for other boards.\"\n#endif\n#include <Adafruit_NeoPixel.h>\n#include \"controller.h\"\n\nconstexpr uint8_t BUTTON_PIN = 2;\nconstexpr uint8_t DATA_PIN = 6;\nconstexpr uint8_t PIXEL_COUNT = 4;\nconstexpr uint8_t BRIGHTNESS = 48;  // 0..255, set once. Not a substitute for power sizing.\nstatic_assert(PIXEL_COUNT >= 1 && PIXEL_COUNT <= 4, \"Recalculate supply before adding pixels.\");\nAdafruit_NeoPixel pixels(PIXEL_COUNT, DATA_PIN, NEO_GRB + NEO_KHZ800);\nStarController controller;\nuint32_t lastFrame = 0;\nStarController::Mode renderedMode = StarController::Off;\n\nvoid setup() {\n  pinMode(BUTTON_PIN, INPUT_PULLUP);\n  Serial.begin(9600);\n  pixels.begin();\n  pixels.setBrightness(BRIGHTNESS);\n  pixels.clear();\n  pixels.show();\n  controller.begin(millis(), digitalRead(BUTTON_PIN) == LOW);\n  Serial.println(F(\"OFF: short click cycles warm/colour/off; hold 1.2s to turn off.\"));\n}\n\nvoid loop() {\n  const uint32_t now = millis();\n  controller.update(digitalRead(BUTTON_PIN) == LOW, now);\n  const StarController::Mode mode = controller.mode();\n  if (mode == renderedMode && uint32_t(now - lastFrame) < 20) return;\n  if (mode != renderedMode) {\n    Serial.print(F(\"Mode: \"));\n    Serial.println(static_cast<uint8_t>(mode));\n  }\n  lastFrame = now;\n  renderedMode = mode;\n  const uint16_t hue = static_cast<uint16_t>(((now % 30000UL) * 65535UL) / 30000UL);\n  for (uint8_t i = 0; i < PIXEL_COUNT; ++i) {\n    uint32_t colour = 0;\n    if (mode == StarController::Warm) colour = pixels.Color(255, 120, 30);\n    if (mode == StarController::Colour) colour = pixels.ColorHSV(hue, 255, 220);\n    pixels.setPixelColor(i, colour);\n  }\n  pixels.show();\n}\n"
        },
        {
          "name": "controller.h",
          "content": "#ifndef CHRISTMAS_STAR_CONTROLLER_H\n#define CHRISTMAS_STAR_CONTROLLER_H\n#include <stdint.h>\n\n// Independent of Arduino: the same interaction logic is exercised by the host tests.\nclass StarController {\n public:\n  enum Mode : uint8_t { Off, Warm, Colour };\n  static const uint32_t DebounceMs = 30;\n  static const uint32_t LongPressMs = 1200;\n  static const uint32_t IdleMs = 600000;\n\n  void begin(uint32_t now, bool pressed) {\n    mode_ = Off;\n    raw_ = stable_ = pressed;\n    suppressUntilRelease_ = pressed;  // Holding the button at boot must not turn the light on.\n    longHandled_ = false;\n    rawChanged_ = pressStarted_ = lastAction_ = now;\n  }\n\n  void update(bool pressed, uint32_t now) {\n    if (pressed != raw_) { raw_ = pressed; rawChanged_ = now; }\n    if (raw_ != stable_ && uint32_t(now - rawChanged_) >= DebounceMs) {\n      stable_ = raw_;\n      if (stable_) {\n        pressStarted_ = now;\n        longHandled_ = false;\n      } else {\n        if (suppressUntilRelease_) {\n          suppressUntilRelease_ = false;\n        } else if (!longHandled_) {\n          mode_ = static_cast<Mode>((static_cast<uint8_t>(mode_) + 1) % 3);\n        }\n        lastAction_ = now;\n      }\n    }\n    if (stable_ && !suppressUntilRelease_ && !longHandled_ &&\n        uint32_t(now - pressStarted_) >= LongPressMs) {\n      mode_ = Off;\n      longHandled_ = true;            // The subsequent release is not a short click.\n      lastAction_ = now;\n    }\n    if (mode_ != Off && uint32_t(now - lastAction_) >= IdleMs) mode_ = Off;\n  }\n  Mode mode() const { return mode_; }\n\n private:\n  Mode mode_ = Off;\n  bool raw_ = false, stable_ = false;\n  bool suppressUntilRelease_ = false, longHandled_ = false;\n  uint32_t rawChanged_ = 0, pressStarted_ = 0, lastAction_ = 0;\n};\n#endif\n"
        }
      ],
      "bundle_b64": "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"
    }
  ]
};
