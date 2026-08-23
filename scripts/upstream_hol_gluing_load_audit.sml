load "glue";
open aiLib kernel graph enum gen glue;

fun ramsey55_env name =
  case OS.Process.getEnv name of
    SOME value => value
  | NONE => raise Fail ("missing environment variable " ^ name);

val ramsey55_label = ramsey55_env "RAMSEY55_GLUE_LABEL";
val ramsey55_pbl = read_pbl (ramsey55_env "RAMSEY55_GLUE_PBL");
val ramsey55_blue = syntax.noclique 24 (4,true);
val ramsey55_red = syntax.noclique 24 (5,false);

fun ramsey55_has wanted terms = List.exists (aconv wanted) terms;

fun ramsey55_load index pairs =
  case pairs of
    [] => ()
  | (left,right) :: rest =>
      let
        val name = "r45_" ^ infts left ^ "_" ^ infts right
        val _ = load (name ^ "Theory")
        val theorem = DB.fetch name name
        val hypotheses = hyp theorem
        val valid =
          aconv (concl theorem) boolSyntax.F andalso
          ramsey55_has ramsey55_blue hypotheses andalso
          ramsey55_has ramsey55_red hypotheses andalso
          not (ramsey55_has boolSyntax.F hypotheses)
        val _ =
          if valid then
            print ("RAMSEY55_" ^ ramsey55_label ^ "_LOAD " ^
                   its index ^ " F C4524B C4524R NO_FALSE_HYP\n")
          else raise Fail ("unexpected theorem shape for " ^ name)
      in
        ramsey55_load (index + 1) rest
      end;

val _ =
  ((ramsey55_load 0 ramsey55_pbl;
    print ("RAMSEY55_" ^ ramsey55_label ^ "_KERNEL_LOAD_" ^
           its (length ramsey55_pbl) ^ "_OK\n");
    OS.Process.exit OS.Process.success)
   handle error =>
     (print ("RAMSEY55_GLUE_KERNEL_AUDIT_FAIL " ^
             General.exnMessage error ^ "\n");
      OS.Process.exit OS.Process.failure));
