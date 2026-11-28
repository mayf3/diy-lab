/-
公理审计（primitives 约定：白名单 = propext, Classical.choice, Quot.sound；出现 sorryAx 即失败）。
运行：cd source-data/christmas-buddy/proof && lake env lean Axioms.lean
-/
import ChristmasBuddy.StateMachine
import ChristmasBuddy.Power
import ChristmasBuddy.Version

#print axioms ChristmasBuddy.thm_sleep_priority
#print axioms ChristmasBuddy.thm_goodnight_silent
#print axioms ChristmasBuddy.thm_no_audio_conflict
#print axioms ChristmasBuddy.thm_goodnight_terminal
#print axioms ChristmasBuddy.thm_fatal_not_goodnight
#print axioms ChristmasBuddy.thm_error_recoverable
#print axioms ChristmasBuddy.thm_return_home_listening
#print axioms ChristmasBuddy.thm_return_home_thinking
#print axioms ChristmasBuddy.thm_return_home_speaking
#print axioms ChristmasBuddy.thm_return_home_magic
#print axioms ChristmasBuddy.thm_return_home_error
#print axioms ChristmasBuddy.thm_return_home_goodnight
#print axioms ChristmasBuddy.thm_wake_returns_idle_safe
#print axioms ChristmasBuddy.Power.thm_magic_within_adapter
#print axioms ChristmasBuddy.Power.thm_worst_within_adapter
#print axioms ChristmasBuddy.Power.thm_led_capped_rail
#print axioms ChristmasBuddy.Power.thm_led_rail_covers_uncapped
#print axioms ChristmasBuddy.Power.thm_rail_sum_bound
#print axioms ChristmasBuddy.Power.thm_3v3_rail
#print axioms ChristmasBuddy.Version.thm_frozen_are_complete
#print axioms ChristmasBuddy.Version.thm_incomplete_never_manufacturable
#print axioms ChristmasBuddy.Version.thm_frozen_manufacturable
#print axioms ChristmasBuddy.Version.thm_complete_sound
#print axioms ChristmasBuddy.Version.thm_unapproved_not_manufacturable
#print axioms ChristmasBuddy.Version.thm_registry_membership_implies_approved
#print axioms ChristmasBuddy.Version.thm_bom_complete_nil
#print axioms ChristmasBuddy.Version.thm_bom_complete_cons
#print axioms ChristmasBuddy.Version.thm_dir_manifest_pure
#print axioms ChristmasBuddy.Version.thm_approval_hash_mismatch_not_manufacturable
#print axioms ChristmasBuddy.Version.thm_approval_release_mismatch_not_manufacturable
