/-!
# Christmas Buddy V1 · M2 设备状态机（Idle/Listening/Thinking/Speaking/Magic/Goodnight/Error）

对应需求：儿童床边圣诞互动机器人。本文件定义状态、事件与转移函数，并证明：
- `thm_sleep_priority`：K4 晚安在**所有状态**下都转移到 Goodnight（最高优先）。
- `thm_goodnight_silent`：Goodnight 状态扬声器关闭（晚安全静音）。
- `thm_no_audio_conflict`：任何状态下麦克风与扬声器不同时开启（I2S 资源互斥）。
- `thm_fatal_not_goodnight`：错误事件不能把 Goodnight 拉出晚安（晚安优先于故障）。
- `thm_error_recoverable`：Error 经 reset 回 Idle（错误可恢复）。
- `thm_return_home_*`：每个状态存在到达 Idle 的事件序列（进展性 witness）。

环境假设（ASM，未在模型内证明，见 proof/README.md）：
- ASM-1：K4 事件总能被送达状态机（ESP32 硬件路径，Pi 死机也可送达）。
- ASM-2：`repeatReq` 在 Idle 触发时存在可重播的上一条回答（否则 UI 层提示）。
- ASM-3：云请求超时由运行时包装为 `cloudFail` 事件（模型不含计时器）。
-/

namespace ChristmasBuddy

/-- 设备状态。 -/
inductive State
  | Idle | Listening | Thinking | Speaking | Magic | Goodnight | Error
  deriving DecidableEq, Repr

/-- 事件（物理按键、云端回调、播放回调）。 -/
inductive Event
  | sleep        -- K4 晚安（最高优先级）
  | wake         -- 晚安唤醒
  | pushToTalk   -- K1 按住说话
  | releaseTalk  -- K1 松开
  | repeatReq    -- K2 重复回答
  | magicReq     -- K3 圣诞魔法灯效
  | cloudDone    -- 云端回答就绪
  | cloudFail    -- 云请求失败/超时
  | speakDone    -- 应答播完
  | magicDone    -- 灯效结束
  | reset        -- 错误恢复（长按 K2 或重启完成）
  | fatal        -- 不可恢复故障（看门狗触发）
  deriving DecidableEq, Repr

open State Event

/-- 转移函数：模式匹配顺序即优先级（sleep > Goodnight 保持 > fatal > 各态正常转移）。 -/
def step : State → Event → State
  | _, sleep => Goodnight
  | Goodnight, wake => Idle
  | Goodnight, _ => Goodnight
  | _, fatal => Error
  | Idle, pushToTalk => Listening
  | Idle, repeatReq => Speaking
  | Idle, magicReq => Magic
  | Idle, _ => Idle
  | Listening, releaseTalk => Thinking
  | Listening, _ => Listening
  | Thinking, cloudDone => Speaking
  | Thinking, cloudFail => Error
  | Thinking, _ => Thinking
  | Speaking, speakDone => Idle
  | Speaking, repeatReq => Speaking
  | Speaking, _ => Speaking
  | Magic, magicDone => Idle
  | Magic, _ => Magic
  | Error, reset => Idle
  | Error, _ => Error

/-- 扬声器是否应处于出声状态。 -/
def speakerOn : State → Bool
  | Speaking => true
  | Magic => true      -- Magic 允许欢快提示音（受 M1 音量帽约束）
  | _ => false

/-- 麦克风是否处于采集状态。 -/
def micOn : State → Bool
  | Listening => true
  | _ => false

/-- 事件序列依序作用于状态。 -/
def applySeq : State → List Event → State := List.foldl step

/-! ### 定理 -/

/-- K4 晚安优先：任何状态下 sleep 都进入 Goodnight。 -/
theorem thm_sleep_priority : ∀ s : State, step s sleep = Goodnight := by
  intro s
  cases s <;> rfl

/-- 晚安全静音：Goodnight 状态扬声器关闭。 -/
theorem thm_goodnight_silent : speakerOn Goodnight = false := rfl

/-- 麦克风与扬声器互斥：不存在两者同时开启的状态。 -/
theorem thm_no_audio_conflict : ∀ s : State, ¬(speakerOn s ∧ micOn s) := by
  intro s
  cases s <;> simp [speakerOn, micOn] <;> constructor <;> simp

/-- 晚安态只被 wake 拉出；其余事件（含 fatal）保持晚安。 -/
theorem thm_goodnight_terminal :
    ∀ e : Event, e ≠ wake → step Goodnight e = Goodnight := by
  intro e he
  cases e <;> first
    | (exfalso; apply he; rfl)
    | rfl

/-- 故障事件不能把 Goodnight 拉出晚安；其余状态的 fatal 都进入 Error。 -/
theorem thm_fatal_not_goodnight :
    ∀ s : State, s ≠ Goodnight → step s fatal = Error := by
  intro s hs
  cases s <;> first
    | (exfalso; apply hs; rfl)
    | rfl

/-- 错误可恢复：Error + reset → Idle。 -/
theorem thm_error_recoverable : step Error reset = Idle := rfl

/-- 进展性：Listening 有到达 Idle 的 witness 路径。 -/
theorem thm_return_home_listening :
    applySeq Listening [releaseTalk, cloudDone, speakDone] = Idle := by decide

/-- 进展性：Thinking。 -/
theorem thm_return_home_thinking :
    applySeq Thinking [cloudDone, speakDone] = Idle := by decide

/-- 进展性：Speaking。 -/
theorem thm_return_home_speaking :
    applySeq Speaking [speakDone] = Idle := by decide

/-- 进展性：Magic。 -/
theorem thm_return_home_magic :
    applySeq Magic [magicDone] = Idle := by decide

/-- 进展性：Error。 -/
theorem thm_return_home_error :
    applySeq Error [reset] = Idle := by decide

/-- 进展性：Goodnight。 -/
theorem thm_return_home_goodnight :
    applySeq Goodnight [wake] = Idle := by decide

/-- 晚安后 wake 回 Idle，且不再残留扬声器状态（由 speakerOn Goodnight = false 保证）。 -/
theorem thm_wake_returns_idle_safe :
    speakerOn (applySeq Goodnight [wake]) = false := by
  decide

end ChristmasBuddy
