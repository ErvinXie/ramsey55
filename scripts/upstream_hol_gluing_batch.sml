load "glue";
open aiLib kernel graph enum gen glue;

fun ramsey55_env name =
  case OS.Process.getEnv name of
    SOME value => value
  | NONE => raise Fail ("missing environment variable " ^ name);

fun ramsey55_positive_int name =
  case Int.fromString (ramsey55_env name) of
    SOME value => if value > 0 then value else raise Fail (name ^ " is not positive")
  | NONE => raise Fail (name ^ " is not an integer");

val ramsey55_label = ramsey55_env "RAMSEY55_GLUE_LABEL";
val ramsey55_pbl = read_pbl (ramsey55_env "RAMSEY55_GLUE_PBL");
val ramsey55_directory = ramsey55_env "RAMSEY55_GLUE_THEORY_DIR";
val ramsey55_expected = ramsey55_positive_int "RAMSEY55_GLUE_EXPECTED_COUNT";
val ramsey55_memory = ramsey55_positive_int "RAMSEY55_GLUE_MEMORY_MB";

fun ramsey55_write_script file (left,right) =
  let
    val left_string = infts left
    val right_string = infts right
    val name = "r45_" ^ left_string ^ "_" ^ right_string
    val lines =
      ["open HolKernel kernel glue",
       "val _ = new_theory " ^ mlquote name,
       "val _ = save_thm (" ^ mlquote name ^
         ", glue_pair (stinf " ^ mlquote left_string ^
         ", stinf " ^ mlquote right_string ^ "))",
       "val _ = export_theory ()"]
  in
    writel file lines
  end;

fun ramsey55_run_one (pair as (left,right)) =
  let
    val file =
      ramsey55_directory ^ "/r45_" ^ infts left ^ "_" ^ infts right ^
      "Script.sml"
  in
    ramsey55_write_script file pair;
    smlExecScripts.exec_script file
  end;

val _ = smlExecScripts.buildheap_dir := ramsey55_directory ^ "/buildheap";
val _ = smlExecScripts.buildheap_options := "--maxheap " ^ its ramsey55_memory;
val _ = app mkDir_err [ramsey55_directory,!smlExecScripts.buildheap_dir];
val _ = writel (ramsey55_directory ^ "/Holmakefile") ["INCLUDES = .."];
val _ =
  print ("RAMSEY55_" ^ ramsey55_label ^ "_MEMORY_MB " ^
         its ramsey55_memory ^ "\n");

fun ramsey55_run index pairs =
  case pairs of
    [] => ()
  | (pair as (left,right)) :: rest =>
      let
        val _ =
          print ("RAMSEY55_" ^ ramsey55_label ^ "_START " ^ its index ^ " " ^
                 infts left ^ " " ^ infts right ^ "\n")
        val _ = ramsey55_run_one pair
        val _ =
          print ("RAMSEY55_" ^ ramsey55_label ^ "_DONE " ^ its index ^ "\n")
      in
        ramsey55_run (index + 1) rest
      end;

val _ =
  ((if length ramsey55_pbl = ramsey55_expected then
      ramsey55_run 0 ramsey55_pbl
    else raise Fail "unexpected gluing problem-list length";
    print ("RAMSEY55_" ^ ramsey55_label ^ "_KERNEL_FULL_" ^
           its ramsey55_expected ^ "_OK\n");
    OS.Process.exit OS.Process.success)
   handle error =>
     (print ("RAMSEY55_GLUE_KERNEL_BUILD_FAIL " ^
             General.exnMessage error ^ "\n");
      OS.Process.exit OS.Process.failure));
