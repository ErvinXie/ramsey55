load "enump";
load "enumf/ramseyEnumTheory";
open HolKernel;

val ramsey55_symmetry = ``!(x:num)(y:num). (E x y : bool) = E y x``;

val ramsey55_expected =
  [("R355", 5, 3, 5, true),
   ("R356", 6, 3, 5, true),
   ("R357", 7, 3, 5, true),
   ("R358", 8, 3, 5, true),
   ("R359", 9, 3, 5, true),
   ("R3510", 10, 3, 5, true),
   ("R3511", 11, 3, 5, true),
   ("R3512", 12, 3, 5, true),
   ("R3513", 13, 3, 5, true),
   ("R3514", 14, 3, 5, false),
   ("R444", 4, 4, 4, true),
   ("R445", 5, 4, 4, true),
   ("R446", 6, 4, 4, true),
   ("R447", 7, 4, 4, true),
   ("R448", 8, 4, 4, true),
   ("R449", 9, 4, 4, true),
   ("R4410", 10, 4, 4, true),
   ("R4411", 11, 4, 4, true),
   ("R4412", 12, 4, 4, true),
   ("R4413", 13, 4, 4, true),
   ("R4414", 14, 4, 4, true),
   ("R4415", 15, 4, 4, true),
   ("R4416", 16, 4, 4, true),
   ("R4417", 17, 4, 4, true),
   ("R4418", 18, 4, 4, false)];

fun ramsey55_has wanted terms = List.exists (aconv wanted) terms;

fun ramsey55_clause size bluen redn blue =
  let
    val name =
      "C" ^ Int.toString bluen ^ Int.toString redn ^ Int.toString size ^
      (if blue then "b" else "r")
    val definition = DB.fetch "ramseyDef" (name ^ "_DEF")
  in
    lhs (concl (SPEC_ALL definition))
  end;

fun ramsey55_cover size bluen redn =
  let
    val name =
      "G" ^ Int.toString bluen ^ Int.toString redn ^ Int.toString size
    val definition = DB.fetch "ramseyDef" (name ^ "_DEF")
  in
    lhs (concl (SPEC_ALL definition))
  end;

fun ramsey55_check (name,size,bluen,redn,has_cover) =
  let
    val theorem = DB.fetch "ramseyEnum" name
    val hypotheses = hyp theorem
    val symmetry = ramsey55_symmetry
    val blue = ramsey55_clause size bluen redn true
    val red = ramsey55_clause size bluen redn false
    val cover_ok =
      if has_cover then
        ramsey55_has (ramsey55_cover size bluen redn) hypotheses
      else true
    val valid =
      aconv (concl theorem) boolSyntax.F andalso
      length hypotheses = (if has_cover then 4 else 3) andalso
      ramsey55_has symmetry hypotheses andalso
      ramsey55_has blue hypotheses andalso
      ramsey55_has red hypotheses andalso
      cover_ok andalso
      not (ramsey55_has boolSyntax.F hypotheses)
    val _ =
      if valid then
        print ("RAMSEY55_ENUMF_LOAD " ^ name ^ " " ^
               Int.toString size ^ " " ^ Int.toString bluen ^ " " ^
               Int.toString redn ^
               " F EXACT_BASE_HYPOTHESES " ^
               (if has_cover then "COVER" else "NO_COVER") ^
               " NO_FALSE_HYP\n")
      else raise Fail ("unexpected theorem shape for " ^ name)
  in
    ()
  end;

val _ =
  ((print "\n";
    app ramsey55_check ramsey55_expected;
    print ("RAMSEY55_ENUMF_KERNEL_LOAD_" ^
           Int.toString (length ramsey55_expected) ^ "_OK\n");
    OS.Process.exit OS.Process.success)
   handle error =>
     (print ("RAMSEY55_ENUMF_KERNEL_AUDIT_FAIL " ^
             General.exnMessage error ^ "\n");
      OS.Process.exit OS.Process.failure));
