import Init.Data.Nat.Lemmas
import Ramsey55.Checker

namespace Ramsey55

/-- Adjacency rows of one public 42-vertex Ramsey(5,5) graph. The rows are
decoded from the first graph6 record in McKay's r55_42some.g6 dataset. -/
def witness42Rows : Array Nat := #[
  1139573399136,
  2500436905360,
  1561790522080,
  3123547570640,
  3562820363146,
  4114865099589,
  2414515753773,
  1586221114142,
  3181056688890,
  2030509228533,
  2787047241731,
  1945372390403,
  202841631841,
  2399245261972,
  409566162066,
  1774326471784,
  1807214769546,
  800857016419,
  506521130131,
  3129522453061,
  3614406380653,
  4149287660702,
  74871674701,
  1894305105695,
  2708288572207,
  1446286176897,
  3162621600066,
  2969010762834,
  1596236953761,
  2674997992774,
  2049442270857,
  4012357005076,
  3909910581405,
  3632353407086,
  1184893368634,
  2900723693109,
  2767499215608,
  1411929027060,
  697785142158,
  3684220768040,
  2919817644725,
  1768137696634
]

theorem witness42Rows_size : witness42Rows.size = 42 := by decide

/-- The natural-number edge function represented by witness42Rows. -/
def witness42RawColoring : RawColoring :=
  fun u v => Nat.testBit (witness42Rows[u]!) v

/-- The Boolean edge colouring represented by witness42Rows. -/
def witness42Coloring : Coloring 42 :=
  fun u v => witness42RawColoring u.val v.val

/-- Kernel-checked certificate chunks. Each theorem covers three possible
first vertices and together they cover all 42 vertices. -/
theorem witness42_check_00_03 :
    checkRamseyFree55Range 42 witness42RawColoring 0 3 = true := by
  decide +kernel

theorem witness42_check_03_06 :
    checkRamseyFree55Range 42 witness42RawColoring 3 3 = true := by
  decide +kernel

theorem witness42_check_06_09 :
    checkRamseyFree55Range 42 witness42RawColoring 6 3 = true := by
  decide +kernel

theorem witness42_check_09_12 :
    checkRamseyFree55Range 42 witness42RawColoring 9 3 = true := by
  decide +kernel

theorem witness42_check_12_15 :
    checkRamseyFree55Range 42 witness42RawColoring 12 3 = true := by
  decide +kernel

theorem witness42_check_15_18 :
    checkRamseyFree55Range 42 witness42RawColoring 15 3 = true := by
  decide +kernel

theorem witness42_check_18_21 :
    checkRamseyFree55Range 42 witness42RawColoring 18 3 = true := by
  decide +kernel

theorem witness42_check_21_24 :
    checkRamseyFree55Range 42 witness42RawColoring 21 3 = true := by
  decide +kernel

theorem witness42_check_24_27 :
    checkRamseyFree55Range 42 witness42RawColoring 24 3 = true := by
  decide +kernel

theorem witness42_check_27_30 :
    checkRamseyFree55Range 42 witness42RawColoring 27 3 = true := by
  decide +kernel

theorem witness42_check_30_33 :
    checkRamseyFree55Range 42 witness42RawColoring 30 3 = true := by
  decide +kernel

theorem witness42_check_33_36 :
    checkRamseyFree55Range 42 witness42RawColoring 33 3 = true := by
  decide +kernel

theorem witness42_check_36_39 :
    checkRamseyFree55Range 42 witness42RawColoring 36 3 = true := by
  decide +kernel

theorem witness42_check_39_42 :
    checkRamseyFree55Range 42 witness42RawColoring 39 3 = true := by
  decide +kernel

private theorem witness42_checkAt (a : Fin 42) :
    checkRamseyFree55At 42 witness42RawColoring a.val = true := by
  by_cases h03 : a.val < 3
  · exact checkRamseyFree55Range_at witness42_check_00_03 (by
      simp [List.mem_range'_1]
      omega)
  by_cases h06 : a.val < 6
  · exact checkRamseyFree55Range_at witness42_check_03_06 (by
      simp [List.mem_range'_1]
      omega)
  by_cases h09 : a.val < 9
  · exact checkRamseyFree55Range_at witness42_check_06_09 (by
      simp [List.mem_range'_1]
      omega)
  by_cases h12 : a.val < 12
  · exact checkRamseyFree55Range_at witness42_check_09_12 (by
      simp [List.mem_range'_1]
      omega)
  by_cases h15 : a.val < 15
  · exact checkRamseyFree55Range_at witness42_check_12_15 (by
      simp [List.mem_range'_1]
      omega)
  by_cases h18 : a.val < 18
  · exact checkRamseyFree55Range_at witness42_check_15_18 (by
      simp [List.mem_range'_1]
      omega)
  by_cases h21 : a.val < 21
  · exact checkRamseyFree55Range_at witness42_check_18_21 (by
      simp [List.mem_range'_1]
      omega)
  by_cases h24 : a.val < 24
  · exact checkRamseyFree55Range_at witness42_check_21_24 (by
      simp [List.mem_range'_1]
      omega)
  by_cases h27 : a.val < 27
  · exact checkRamseyFree55Range_at witness42_check_24_27 (by
      simp [List.mem_range'_1]
      omega)
  by_cases h30 : a.val < 30
  · exact checkRamseyFree55Range_at witness42_check_27_30 (by
      simp [List.mem_range'_1]
      omega)
  by_cases h33 : a.val < 33
  · exact checkRamseyFree55Range_at witness42_check_30_33 (by
      simp [List.mem_range'_1]
      omega)
  by_cases h36 : a.val < 36
  · exact checkRamseyFree55Range_at witness42_check_33_36 (by
      simp [List.mem_range'_1]
      omega)
  by_cases h39 : a.val < 39
  · exact checkRamseyFree55Range_at witness42_check_36_39 (by
      simp [List.mem_range'_1]
      omega)
  exact checkRamseyFree55Range_at witness42_check_39_42 (by
    simp [List.mem_range'_1]
    omega)

/-- The embedded graph is symmetric and loop-free. -/
theorem witness42_simple : IsSimpleColoring witness42Coloring := by
  unfold IsSimpleColoring
  decide +kernel

/-- The embedded graph has no monochromatic K_5. -/
theorem witness42_ramseyFree : IsRamseyFree55 witness42Coloring :=
  fun a => checkRamseyFree55At_sound a (witness42_checkAt a)

/-- Formal lower bound: 42 vertices do not force a monochromatic K_5. -/
theorem not_forcesMonochromatic5_42 : ¬ ForcesMonochromatic5 42 := by
  intro forced
  exact forced witness42Coloring witness42_simple witness42_ramseyFree

#print axioms witness42_simple
#print axioms witness42_ramseyFree
#print axioms not_forcesMonochromatic5_42

end Ramsey55
