; HEADER_BLOCK_START
; BambuStudio 02.08.02.61
; model printing time: 15m 13s; total estimated time: 15m 32s
; total layer number: 27
; total filament length [mm] : 2058.49
; total filament volume [cm^3] : 4951.25
; total filament weight [g] : 6.19
; model label id: 8,12,16
; object max height: 5.40,3.20,3.20
; filament_density: 1.25
; filament_diameter: 1.75
; max_z_height: 5.40
; filament: 1
; support_material_on_wipe_tower: 0
; HEADER_BLOCK_END

; CONFIG_BLOCK_START
; accel_to_decel_enable = 0
; accel_to_decel_factor = 50%
; activate_air_filtration = 0
; additional_cooling_fan_speed = 0
; additional_fan_full_speed_layer = 0
; alternate_extra_wall = 0
; ams_filament_load_time_ams = 0
; ams_filament_load_time_ams_lite = 0
; ams_filament_load_time_n3f_s = 0
; ams_filament_unload_time_ams = 0
; ams_filament_unload_time_ams_lite = 0
; ams_filament_unload_time_n3f_s = 0
; apply_scarf_seam_on_circles = 1
; auxiliary_fan = 1
; avoid_crossing_wall_includes_support = 0
; bed_custom_model = 
; bed_custom_texture = 
; bed_exclude_area = 
; bed_heat_soak_area = 
; bed_temperature_formula = by_highest_temp
; before_layer_change_gcode = 
; best_object_pos = 0.3,0.5
; bottom_color_penetration_layers = 3
; bottom_shell_layers = 6
; bottom_shell_thickness = 0
; bottom_surface_density = 100%
; bottom_surface_pattern = monotonic
; bridge_angle = 0
; bridge_flow = 1
; bridge_no_support = 1
; bridge_speed = 50,50
; brim_object_gap = 0.1
; brim_type = no_brim
; brim_width = 5
; chamber_temperatures = 0
; change_filament_gcode = M620 S[next_extruder]A\nM204 S9000\nG1 Z{max_layer_z + 8.0} F1200\n\nM400\nM106 P1 S0\nM106 P2 S0\n{if old_filament_temp > 142 && next_extruder < 255}\nM104 S[old_filament_temp]\n{endif}\n{if toolchange_count == 2}\n; get travel path for change filament\n;M620.1 X[travel_point_1_x] Y[travel_point_1_y] F21000 P0\n;M620.1 X[travel_point_2_x] Y[travel_point_2_y] F21000 P1\n;M620.1 X[travel_point_3_x] Y[travel_point_3_y] F21000 P2\n{endif}\n\nM620.10 A0 F[old_filament_e_feedrate] L[flush_length] H{nozzle_diameter[previous_extruder]} T{nozzle_temperature_range_high[previous_extruder]} P[old_filament_temp]\nM620.10 A1 F[new_filament_e_feedrate] L[flush_length] H{nozzle_diameter[next_extruder]} T{nozzle_temperature_range_high[next_extruder]} P[new_filament_temp]\n\nT[next_extruder]\nM400\nM83\n{if next_extruder < 255}\n\nM628 S0\n\n{if flush_length_1 > 1}\n; FLUSH_START\n; always use highest temperature to flush\nM400\nM1002 set_filament_type:UNKNOWN\nM109 S[nozzle_temperature_range_high]\n{if flush_length_1 > 23.7}\nG1 E23.7 F{old_filament_e_feedrate} ; do not need pulsatile flushing for start part\nG1 E{(flush_length_1 - 23.7) * 0.02} F50\nG1 E{(flush_length_1 - 23.7) * 0.23} F{old_filament_e_feedrate}\nG1 E{(flush_length_1 - 23.7) * 0.02} F50\nG1 E{(flush_length_1 - 23.7) * 0.23} F{new_filament_e_feedrate}\nG1 E{(flush_length_1 - 23.7) * 0.02} F50\nG1 E{(flush_length_1 - 23.7) * 0.23} F{new_filament_e_feedrate}\nG1 E{(flush_length_1 - 23.7) * 0.02} F50\nG1 E{(flush_length_1 - 23.7) * 0.23} F{new_filament_e_feedrate}\n{else}\nG1 E{flush_length_1} F{old_filament_e_feedrate}\n{endif}\n; FLUSH_END\nG1 E-[old_retract_length_toolchange] F1800\nG1 E[old_retract_length_toolchange] F300\nM400\nM1002 set_filament_type:{filament_type[next_extruder]}\n{endif}\n\n{if flush_length_1 > 45 && flush_length_2 > 1}\n; WIPE\nM400\nM106 P1 S255\nM400 S3\nG1 Y327.6 F20000\nG1 Y336 F9000\nG1 Y327.6 F20000\nG1 Y336 F9000\nM400\nM106 P1 S0\n{endif}\n\n{if flush_length_2 > 1}\n; FLUSH_START\nG1 E{flush_length_2 * 0.18} F{new_filament_e_feedrate}\nG1 E{flush_length_2 * 0.02} F50\nG1 E{flush_length_2 * 0.18} F{new_filament_e_feedrate}\nG1 E{flush_length_2 * 0.02} F50\nG1 E{flush_length_2 * 0.18} F{new_filament_e_feedrate}\nG1 E{flush_length_2 * 0.02} F50\nG1 E{flush_length_2 * 0.18} F{new_filament_e_feedrate}\nG1 E{flush_length_2 * 0.02} F50\nG1 E{flush_length_2 * 0.18} F{new_filament_e_feedrate}\nG1 E{flush_length_2 * 0.02} F50\n; FLUSH_END\nG1 E-[new_retract_length_toolchange] F1800\nG1 E[new_retract_length_toolchange] F300\n{endif}\n\n{if flush_length_2 > 45 && flush_length_3 > 1}\n; WIPE\nM400\nM106 P1 S255\nM400 S3\nG1 Y327.6 F20000\nG1 Y336 F9000\nG1 Y327.6 F20000\nG1 Y336 F9000\nM400\nM106 P1 S0\n{endif}\n\n{if flush_length_3 > 1}\n\n; FLUSH_START\nG1 E{flush_length_3 * 0.18} F{new_filament_e_feedrate}\nG1 E{flush_length_3 * 0.02} F50\nG1 E{flush_length_3 * 0.18} F{new_filament_e_feedrate}\nG1 E{flush_length_3 * 0.02} F50\nG1 E{flush_length_3 * 0.18} F{new_filament_e_feedrate}\nG1 E{flush_length_3 * 0.02} F50\nG1 E{flush_length_3 * 0.18} F{new_filament_e_feedrate}\nG1 E{flush_length_3 * 0.02} F50\nG1 E{flush_length_3 * 0.18} F{new_filament_e_feedrate}\nG1 E{flush_length_3 * 0.02} F50\n; FLUSH_END\nG1 E-[new_retract_length_toolchange] F1800\nG1 E[new_retract_length_toolchange] F300\n{endif}\n\n{if flush_length_3 > 45 && flush_length_4 > 1}\n; WIPE\nM400\nM106 P1 S255\nM400 S3\nG1 Y327.6 F20000\nG1 Y336 F9000\nG1 Y327.6 F20000\nG1 Y336 F9000\nM400\nM106 P1 S0\n{endif}\n\n{if flush_length_4 > 1}\n; FLUSH_START\nG1 E{flush_length_4 * 0.18} F{new_filament_e_feedrate}\nG1 E{flush_length_4 * 0.02} F50\nG1 E{flush_length_4 * 0.18} F{new_filament_e_feedrate}\nG1 E{flush_length_4 * 0.02} F50\nG1 E{flush_length_4 * 0.18} F{new_filament_e_feedrate}\nG1 E{flush_length_4 * 0.02} F50\nG1 E{flush_length_4 * 0.18} F{new_filament_e_feedrate}\nG1 E{flush_length_4 * 0.02} F50\nG1 E{flush_length_4 * 0.18} F{new_filament_e_feedrate}\nG1 E{flush_length_4 * 0.02} F50\n; FLUSH_END\n{endif}\n\nM400\nM109 S[new_filament_temp]\nG1 E2 F60 ;Compensate for filament spillage during waiting temperature\n\nM400\nG92 E0\nG1 E-[new_retract_length_toolchange] F1800\nM400\nM106 P1 S255\nM400 S3\nG1 Y327.6 F20000\nG1 Y336 F9000\nG1 Y327.6 F20000\nG1 Y336 F9000\nG1 Y327.6 F20000\nM400\nM106 P1 S0\n\nM629\n\nM400\n{else}\nG1 X[x_after_toolchange] Y[y_after_toolchange] Z[z_after_toolchange] F12000\n{endif}\nM400\nM83\nG1 Y295 F30000\nG1 Y265 F18000\n{if layer_z <= (initial_layer_print_height + 0.001)}\nM204 S[initial_layer_acceleration]\n{else}\nM204 S[default_acceleration]\n{endif}\nM621 S[next_extruder]A\nG1 Z{max_layer_z + 3.0} F3000\n\n
; circle_compensation_manual_offset = 0
; circle_compensation_speed = 200
; close_additional_fan_first_x_layers = 3
; close_fan_the_first_x_layers = 3
; compatible_printers_condition = 
; complete_print_exhaust_fan_speed = 70
; cool_plate_temp = 0
; cool_plate_temp_initial_layer = 0
; cooling_filter_enabled = 0
; cooling_perimeter_transition_distance = 10
; cooling_slowdown_logic = uniform_cooling
; counter_coef_1 = 0
; counter_coef_2 = 0.008
; counter_coef_3 = -0.041
; counter_limit_max = 0.033
; counter_limit_min = -0.035
; counterbore_hole_bridging = none
; curr_bed_type = Textured PEI Plate
; default_acceleration = 8000,8000
; default_ams_type = -1
; default_filament_colour = ""
; default_filament_profile = "Bambu PLA Basic @BBL H2D"
; default_jerk = 0
; default_nozzle_volume_type = Standard,Standard
; default_print_profile = 0.20mm Standard @BBL H2D
; deretraction_speed = 30,30
; detect_floating_vertical_shell = 1
; detect_narrow_internal_solid_infill = 1
; detect_overhang_wall = 1
; detect_thin_wall = 0
; diameter_limit = 50
; different_settings_to_system = ;;
; draft_shield = disabled
; during_print_exhaust_fan_speed = 70
; elefant_foot_compensation = 0.15
; embedding_wall_into_infill = 0
; enable_arc_fitting = 1
; enable_circle_compensation = 0
; enable_filament_dynamic_map = 0
; enable_height_slowdown = 0,0
; enable_long_retraction_when_cut = 2
; enable_mixed_color_sublayer = 0
; enable_order_independent_overlap_carving = 0
; enable_overhang_bridge_fan = 1
; enable_overhang_speed = 1,1
; enable_pre_heating = 1
; enable_pressure_advance = 0
; enable_prime_tower = 1
; enable_support = 0
; enable_support_ironing = 0
; enable_tower_interface_features = 1
; enable_wrapping_detection = 0
; enforce_support_layers = 0
; eng_plate_temp = 70
; eng_plate_temp_initial_layer = 70
; ensure_vertical_shell_thickness = enabled
; exclude_object = 1
; extruder_ams_count = 1#0|4#1;1#0|4#1
; extruder_clearance_dist_to_rod = 50
; extruder_clearance_height_to_lid = 201
; extruder_clearance_height_to_rod = 47.4
; extruder_clearance_max_radius = 96
; extruder_colour = #018001;#018001
; extruder_max_nozzle_count = 1,1
; extruder_nozzle_stats = Standard#1;Standard#1
; extruder_offset = 0x0,0x0
; extruder_printable_area = 0x0,325x0,325x320,0x320#25x0,350x0,350x320,25x320
; extruder_printable_height = 320,325
; extruder_type = Direct Drive,Direct Drive
; extruder_variant_list = "Direct Drive Standard,Direct Drive High Flow,Direct Drive E3D High Flow";"Direct Drive Standard,Direct Drive High Flow,Direct Drive TPU High Flow,Direct Drive E3D High Flow"
; fan_cooling_layer_time = 30
; fan_direction = left
; fan_max_speed = 30
; fan_min_speed = 20
; farthest_point_timelapse = 1
; filament_adaptive_volumetric_speed = 0
; filament_adhesiveness_category = 300
; filament_bridge_speed = 25
; filament_change_length = 4
; filament_change_length_nc = 10
; filament_colour = #00AE42
; filament_cooling_before_tower = 10
; filament_cost = 17.99
; filament_density = 1.25
; filament_dev_ams_drying_ams_limitations = 1
; filament_dev_ams_drying_heat_distortion_temperature = 75
; filament_dev_ams_drying_temperature = 65
; filament_dev_ams_drying_time = 12
; filament_dev_chamber_drying_bed_temperature = 80
; filament_dev_chamber_drying_time = 12
; filament_dev_drying_cooling_temperature = 55
; filament_dev_drying_softening_temperature = 60
; filament_diameter = 1.75
; filament_enable_overhang_speed = 1
; filament_end_gcode = "; filament end gcode \n"
; filament_extruder_compatibility = 0
; filament_extruder_variant = "Direct Drive Standard"
; filament_flow_ratio = 0.95
; filament_flush_temp = 0
; filament_flush_temp_fast = 0
; filament_flush_volumetric_speed = 0
; filament_ids = GFG00
; filament_is_mixed = 0
; filament_is_support = 0
; filament_map = 1
; filament_map_2 = 0
; filament_map_mode = Auto For Flush
; filament_max_volumetric_speed = 18
; filament_metal_stickiness = High
; filament_minimal_purge_on_wipe_tower = 15
; filament_mixed_components = ""
; filament_mixed_gradient = 0
; filament_mixed_gradient_curve = ""
; filament_mixed_gradient_per_part = 0
; filament_mixed_gradient_range = ""
; filament_mixed_sublayer_ratios = ""
; filament_notes = 
; filament_nozzle_map = 0
; filament_overhang_1_4_speed = 0
; filament_overhang_2_4_speed = 50
; filament_overhang_3_4_speed = 30
; filament_overhang_4_4_speed = 10
; filament_overhang_totally_speed = 10
; filament_pre_cooling_temperature = 0
; filament_pre_cooling_temperature_nc = 0
; filament_preheat_temperature_delta = 0
; filament_prime_volume = 30
; filament_prime_volume_nc = 60
; filament_printable = 3
; filament_ramming_travel_time = 0
; filament_ramming_travel_time_nc = 0
; filament_ramming_volumetric_speed = -1
; filament_ramming_volumetric_speed_nc = -1
; filament_retract_length_nc = 14
; filament_retraction_length = 0.4
; filament_scarf_gap = 0%
; filament_scarf_height = 10%
; filament_scarf_length = 10
; filament_scarf_seam_type = none
; filament_self_index = 1
; filament_settings_id = "Bambu PETG Basic @BBL H2D 0.4 nozzle"
; filament_shrink = 100%
; filament_soluble = 0
; filament_start_gcode = "; filament start gcode\n"
; filament_tower_interface_pre_extrusion_dist = 10
; filament_tower_interface_pre_extrusion_length = 0
; filament_tower_interface_print_temp = -1
; filament_tower_interface_purge_volume = 20
; filament_tower_ironing_area = 8
; filament_type = PETG
; filament_velocity_adaptation_factor = 1
; filament_vendor = "Bambu Lab"
; filament_volume_map = 0
; filament_wipe = 1
; filament_wipe_distance = 1
; filament_z_hop_types = Spiral Lift
; filename_format = {input_filename_base}_{filament_type[0]}_{print_time}.gcode
; fill_multiline = 1
; filter_out_gap_fill = 0
; first_layer_print_sequence = 0
; first_x_layer_fan_speed = 0
; first_x_layer_part_fan_speed = 0
; flush_into_infill = 0
; flush_into_objects = 0
; flush_into_support = 1
; flush_multiplier = 1
; flush_multiplier_fast = 1.2
; flush_volumes_matrix = 0,280,280,280,280,0,280,280,280,280,0,280,280,280,280,0
; flush_volumes_vector = 140,140,140,140,140,140,140,140
; full_fan_speed_layer = 0
; fuzzy_skin = none
; fuzzy_skin_first_layer = 0
; fuzzy_skin_mode = displacement
; fuzzy_skin_noise_type = classic
; fuzzy_skin_octaves = 4
; fuzzy_skin_persistence = 0.5
; fuzzy_skin_point_distance = 0.8
; fuzzy_skin_scale = 1
; fuzzy_skin_thickness = 0.3
; gap_infill_speed = 250,250
; gcode_add_line_number = 0
; gcode_flavor = marlin
; grab_length = 0,0
; group_algo_with_time = 0
; has_filament_switcher = 0
; has_scarf_joint_seam = 0
; head_wrap_detect_zone = 
; hole_coef_1 = 0
; hole_coef_2 = -0.008
; hole_coef_3 = 0.23415
; hole_limit_max = 0.22
; hole_limit_min = 0.088
; hot_plate_temp = 70
; hot_plate_temp_initial_layer = 70
; hotend_cooling_rate = 2,2
; hotend_heating_rate = 3.6,3.6
; impact_strength_z = 13.6
; independent_support_layer_height = 1
; infill_combination = 0
; infill_direction = 45
; infill_instead_top_bottom_surfaces = 0
; infill_jerk = 9
; infill_lock_depth = 1
; infill_rotate_step = 0
; infill_shift_step = 0.4
; infill_wall_overlap = 15%
; inherits_group = ;;
; initial_layer_acceleration = 500,500
; initial_layer_flow_ratio = 1
; initial_layer_infill_speed = 105,105
; initial_layer_jerk = 9
; initial_layer_line_width = 0.5
; initial_layer_print_height = 0.2
; initial_layer_speed = 50,50
; initial_layer_travel_acceleration = 6000,6000
; inner_wall_acceleration = 0,0
; inner_wall_jerk = 9
; inner_wall_line_width = 0.45
; inner_wall_speed = 300,300
; interface_shells = 0
; interlocking_beam = 0
; interlocking_beam_layer_count = 2
; interlocking_beam_width = 0.8
; interlocking_boundary_avoidance = 2
; interlocking_depth = 2
; interlocking_orientation = 22.5
; internal_bridge_support_thickness = 0.8
; internal_solid_infill_line_width = 0.42
; internal_solid_infill_pattern = zig-zag
; internal_solid_infill_speed = 250,250
; ironing_direction = 45
; ironing_fan_speed = -1
; ironing_flow = 10%
; ironing_inset = 0.21
; ironing_pattern = zig-zag
; ironing_spacing = 0.15
; ironing_speed = 30
; ironing_type = no ironing
; is_infill_first = 0
; layer_change_gcode = ; layer num/total_layer_count: {layer_num+1}/[total_layer_count]\n; update layer progress\nM73 L{layer_num+1}\nM991 S0 P{layer_num} ;notify layer change
; layer_height = 0.2
; line_width = 0.42
; locked_skeleton_infill_pattern = zigzag
; locked_skin_infill_pattern = crosszag
; long_retractions_when_cut = 0,0
; long_retractions_when_ec = 0
; machine_bed_mass_Y = 0
; machine_end_gcode = ;===== date: 20230428 =====================\nM400 ; wait for buffer to clear\nG92 E0 ; zero the extruder\nG1 E-0.8 F1800 ; retract\nG1 Z{max_layer_z + 0.5} F900 ; lower z a little\nG1 X65 Y245 F12000 ; move to safe pos \nG1 Y265 F3000\n\nG1 X65 Y245 F12000\nG1 Y265 F3000\nM140 S0 ; turn off bed\nM106 S0 ; turn off fan\nM106 P2 S0 ; turn off remote part cooling fan\nM106 P3 S0 ; turn off chamber cooling fan\n\nG1 X100 F12000 ; wipe\n; pull back filament to AMS\nM620 S255\nG1 X20 Y50 F12000\nG1 Y-3\nT255\nG1 X65 F12000\nG1 Y265\nG1 X100 F12000 ; wipe\nM621 S255\nM104 S0 ; turn off hotend\n\nM622.1 S1 ; for prev firmware, default turned on\nM1002 judge_flag timelapse_record_flag\nM622 J1\n    M400 ; wait all motion done\n    M991 S0 P-1 ;end smooth timelapse at safe pos\n    M400 S3 ;wait for last picture to be taken\nM623; end of \"timelapse_record_flag\"\n\nM400 ; wait all motion done\nM17 S\nM17 Z0.4 ; lower z motor current to reduce impact if there is something in the bottom\n{if (max_layer_z + 100.0) < 250}\n    G1 Z{max_layer_z + 100.0} F600\n    G1 Z{max_layer_z +98.0}\n{else}\n    G1 Z250 F600\n    G1 Z248\n{endif}\nM400 P100\nM17 R ; restore z current\n\nG90\nG1 X128 Y250 F3600\n\nM220 S100  ; Reset feedrate magnitude\nM201.2 K1.0 ; Reset acc magnitude\nM73.2   R1.0 ;Reset left time magnitude\nM1002 set_gcode_claim_speed_level : 0\n\nM17 X0.8 Y0.8 Z0.5 ; lower motor current to 45% power\n
; machine_hotend_change_time = 0
; machine_load_filament_time = 26
; machine_max_acceleration_e = 5000,5000,5000,5000
; machine_max_acceleration_extruding = 20000,20000,20000,20000
; machine_max_acceleration_retracting = 5000,5000,5000,5000
; machine_max_acceleration_travel = 9000,9000,9000,9000
; machine_max_acceleration_x = 20000,20000,20000,20000
; machine_max_acceleration_y = 20000,20000,20000,20000
; machine_max_acceleration_z = 500,500,500,500
; machine_max_force_Y = 0
; machine_max_jerk_e = 2.5,2.5,2.5,2.5
; machine_max_jerk_x = 9,9,9,9
; machine_max_jerk_y = 9,9,9,9
; machine_max_jerk_z = 3,3,3,3
; machine_max_printed_mass = 0
; machine_max_speed_e = 50,50,50,50
; machine_max_speed_x = 1000,1000,1000,1000
; machine_max_speed_y = 1000,1000,1000,1000
; machine_max_speed_z = 30,30,30,30
; machine_min_extruding_rate = 0,0
; machine_min_travel_rate = 0,0
; machine_pause_gcode = M400 U1
; machine_prepare_compensation_time = 260
; machine_start_gcode = G0 Z20 F9000\nG92 E0; G1 E-10 F1200\nG28\nM970 Q1 A10 B10 C130 K0\nM970 Q1 A10 B131 C250 K1\nM974 Q1 S1 P0\nM970 Q0 A10 B10 C130 H20 K0\nM970 Q0 A10 B131 C250 K1\nM974 Q0 S1 P0\nM220 S100 ;Reset Feedrate\nM221 S100 ;Reset Flowrate\nG29 ;Home\nG90;\nG92 E0 ;Reset Extruder \nG1 Z2.0 F3000 ;Move Z Axis up \nG1 X10.1 Y20 Z0.28 F5000.0 ;Move to start position\nM109 S205;\nG1 X10.1 Y200.0 Z0.28 F1500.0 E15 ;Draw the first line\nG1 X10.4 Y200.0 Z0.28 F5000.0 ;Move to side a little\nG1 X10.4 Y20 Z0.28 F1500.0 E30 ;Draw the second line\nG92 E0 ;Reset Extruder \nG1 X110 Y110 Z2.0 F3000 ;Move Z Axis up
; machine_switch_extruder_time = 5.6
; machine_unload_filament_time = 26
; master_extruder_id = 2
; max_bridge_length = 0
; max_layer_height = 0.28,0.28
; max_travel_detour_distance = 0
; min_bead_width = 85%
; min_feature_size = 25%
; min_layer_height = 0.08,0.08
; minimum_sparse_infill_area = 15
; mmu_segmented_region_interlocking_depth = 0
; mmu_segmented_region_max_width = 0
; monotonic_travel_into_wall = 45%
; no_slow_down_for_cooling_on_outwalls = 0
; nozzle_diameter = 0.4,0.4
; nozzle_flush_dataset = 1,1
; nozzle_height = 4
; nozzle_temperature = 250
; nozzle_temperature_initial_layer = 245
; nozzle_temperature_range_high = 270
; nozzle_temperature_range_low = 230
; nozzle_type = hardened_steel,hardened_steel
; nozzle_volume = 130,145
; nozzle_volume_type = Standard,Standard
; only_one_wall_first_layer = 0
; ooze_prevention = 0
; other_layers_print_sequence = 0
; other_layers_print_sequence_nums = 0
; outer_wall_acceleration = 5000,5000
; outer_wall_jerk = 9
; outer_wall_line_width = 0.42
; outer_wall_speed = 200,200
; overhang_1_4_speed = 0,0
; overhang_2_4_speed = 50,50
; overhang_3_4_speed = 30,30
; overhang_4_4_speed = 10,10
; overhang_fan_speed = 50
; overhang_fan_threshold = 10%
; overhang_threshold_participating_cooling = 95%
; overhang_totally_speed = 10,10
; override_filament_scarf_seam_setting = 0
; override_process_overhang_speed = 0
; physical_extruder_map = 1,0
; post_process = 
; pre_start_fan_time = 2
; precise_outer_wall = 0
; precise_z_height = 0
; pressure_advance = 0.02
; prime_tower_brim_width = -1
; prime_tower_enable_framework = 0
; prime_tower_extra_rib_length = 0
; prime_tower_fillet_wall = 1
; prime_tower_flat_ironing = 1
; prime_tower_infill_gap = 150%
; prime_tower_lift_height = -1
; prime_tower_lift_speed = 90
; prime_tower_max_speed = 90
; prime_tower_rib_wall = 1
; prime_tower_rib_width = 8
; prime_tower_skip_points = 1
; prime_tower_width = 60
; prime_volume_mode = Default
; print_compatible_printers = "Bambu Lab H2D 0.4 nozzle"
; print_extruder_id = 1,2
; print_extruder_variant = "Direct Drive Standard";"Direct Drive Standard"
; print_flow_ratio = 1
; print_in_clockwise = 0
; print_sequence = by layer
; print_settings_id = Alignment tools PETG 0.20 H2D
; printable_area = 0x0,350x0,350x320,0x320
; printable_height = 325
; printer_extruder_id = 1,2
; printer_extruder_variant = "Direct Drive Standard";"Direct Drive Standard"
; printer_model = Bambu Lab H2D
; printer_notes = 
; printer_settings_id = Bambu Lab H2D 0.4 nozzle
; printer_structure = corexy
; printer_technology = FFF
; printer_variant = 0.4
; printing_by_object_gcode = 
; process_notes = 
; raft_contact_distance = 0.1
; raft_expansion = 1.5
; raft_first_layer_density = 90%
; raft_first_layer_expansion = -1
; raft_layers = 0
; reduce_crossing_wall = 0
; reduce_fan_stop_start_freq = 1
; reduce_infill_retraction_mode = Auto
; required_nozzle_HRC = 3
; resolution = 0.012
; retract_before_wipe = 0%,0%
; retract_length_toolchange = 2,2
; retract_lift_above = 0,0
; retract_lift_below = 319,319
; retract_restart_extra = 0,0
; retract_restart_extra_toolchange = 0,0
; retract_when_changing_layer = 1,1
; retraction_distances_when_cut = 10,10
; retraction_distances_when_ec = 0
; retraction_length = 0.8,0.8
; retraction_minimum_travel = 1,1
; retraction_speed = 30,30
; role_base_wipe_speed = 1
; scan_first_layer = 0
; scarf_angle_threshold = 155
; seam_gap = 15%
; seam_placement_away_from_overhangs = 0
; seam_position = aligned
; seam_slope_conditional = 1
; seam_slope_entire_loop = 0
; seam_slope_gap = 0
; seam_slope_inner_walls = 1
; seam_slope_min_length = 10
; seam_slope_start_height = 10%
; seam_slope_steps = 10
; seam_slope_type = none
; silent_mode = 0
; single_extruder_multi_material = 1
; skeleton_infill_density = 15%
; skeleton_infill_line_width = 0.45
; skin_infill_density = 15%
; skin_infill_depth = 2
; skin_infill_line_width = 0.45
; skirt_distance = 2
; skirt_height = 1
; skirt_loops = 0
; skirt_per_object = 1
; slice_closing_radius = 0.049
; slicing_mode = regular
; slow_down_for_layer_cooling = 1
; slow_down_layer_time = 12
; slow_down_min_speed = 10
; slowdown_end_acc = 100000,100000
; slowdown_end_height = 400,400
; slowdown_end_speed = 1000,1000
; slowdown_start_acc = 100000,100000
; slowdown_start_height = 0,0
; slowdown_start_speed = 1000,1000
; small_perimeter_speed = 50%,50%
; small_perimeter_threshold = 0,0
; smooth_coefficient = 4
; smooth_speed_discontinuity_area = 1
; solid_infill_filament = 0
; sparse_infill_acceleration = 100%,100%
; sparse_infill_anchor = 400%
; sparse_infill_anchor_max = 20
; sparse_infill_density = 99%
; sparse_infill_filament = 0
; sparse_infill_lattice_angle_1 = -45
; sparse_infill_lattice_angle_2 = 45
; sparse_infill_line_width = 0.45
; sparse_infill_pattern = cubic
; sparse_infill_speed = 350,350
; spiral_mode = 0
; spiral_mode_max_xy_smoothing = 200%
; spiral_mode_smooth = 0
; standby_temperature_delta = -5
; start_end_points = 30x-3,54x245
; supertack_plate_temp = 60
; supertack_plate_temp_initial_layer = 60
; support_air_filtration = 0
; support_angle = 0
; support_base_pattern = rectilinear
; support_base_pattern_spacing = 4
; support_bottom_interface_spacing = 0.5
; support_bottom_z_distance = 0.24
; support_chamber_temp_control = 1
; support_cooling_filter = 1
; support_critical_regions_only = 1
; support_expansion = 0
; support_fast_purge_mode = 0
; support_filament = 0
; support_interface_bottom_layers = 2
; support_interface_filament = 0
; support_interface_loop_pattern = 0
; support_interface_not_for_body = 1
; support_interface_pattern = auto
; support_interface_spacing = 0.6
; support_interface_speed = 80,80
; support_interface_top_layers = 2
; support_ironing_direction = 0
; support_ironing_flow = 10%
; support_ironing_inset = 0
; support_ironing_pattern = zig-zag
; support_ironing_spacing = 0.15
; support_ironing_speed = 30
; support_line_width = 0.42
; support_object_first_layer_gap = 0.2
; support_object_skip_flush = 0
; support_object_xy_distance = 0.5
; support_on_build_plate_only = 1
; support_remove_small_overhang = 1
; support_speed = 150,150
; support_style = snug
; support_threshold_angle = 30
; support_top_z_distance = 0.24
; support_type = normal(auto)
; symmetric_infill_y_axis = 0
; temperature_vitrification = 60
; template_custom_gcode = 
; textured_plate_temp = 70
; textured_plate_temp_initial_layer = 70
; thick_bridges = 0
; thumbnail_size = 50x50
; time_lapse_gcode = ;========Date 20250206========\nM622.1 S1 ; for prev firmware, default turned on\nM1002 judge_flag timelapse_record_flag\nM622 J1\n{if timelapse_type == 0} ; timelapse without wipe tower\nM971 S11 C10 O0 T3000\n{elsif timelapse_type == 1} ; timelapse with wipe tower\nG92 E0\nG1 X65 Y245 F20000 ; move to safe pos\nG17\nG2 Z{layer_z} I0.86 J0.86 P1 F20000\nG1 Y265 F3000\nM400 P300\nM971 S11 C10 O0 T3000\nG92 E0\nG1 X100 F5000\nG1 Y255 F20000\n{endif}\nM623\n
; timelapse_type = 0
; top_area_threshold = 200%
; top_color_penetration_layers = 5
; top_one_wall_type = all top
; top_shell_layers = 6
; top_shell_thickness = 1
; top_solid_infill_flow_ratio = 1,1
; top_surface_acceleration = 2000,2000
; top_surface_density = 100%
; top_surface_jerk = 9
; top_surface_line_width = 0.42
; top_surface_pattern = monotonicline
; top_surface_speed = 200,200
; top_z_overrides_xy_distance = 0
; travel_acceleration = 10000,10000
; travel_jerk = 9
; travel_short_distance_acceleration = 250,250
; travel_speed = 1000,1000
; travel_speed_z = 0,0
; tree_support_branch_angle = 45
; tree_support_branch_diameter = 2
; tree_support_branch_diameter_angle = 5
; tree_support_branch_distance = 5
; tree_support_wall_count = -1
; upward_compatible_machine = "Bambu Lab H2D Pro 0.4 nozzle"
; use_firmware_retraction = 0
; use_relative_e_distances = 1
; vertical_shell_speed = 80%,80%
; volumetric_speed_coefficients = "0 0 0 0 0 0"
; wall_distribution_count = 1
; wall_filament = 0
; wall_generator = classic
; wall_loops = 4
; wall_sequence = inner wall/outer wall
; wall_transition_angle = 10
; wall_transition_filter_deviation = 25%
; wall_transition_length = 100%
; wipe = 1,1
; wipe_distance = 2,2
; wipe_speed = 80%
; wipe_tower_no_sparse_layers = 0
; wipe_tower_rotation_angle = 0
; wipe_tower_x = 15
; wipe_tower_y = 220
; wrapping_detection_gcode = 
; wrapping_detection_layers = 20
; wrapping_exclude_area = 145x310,256x310,256x326,145x326
; xy_contour_compensation = 0
; xy_hole_compensation = 0
; z_direction_outwall_speed_continuous = 1
; z_hop = 0.4,0.4
; z_hop_types = Auto Lift,Auto Lift
; CONFIG_BLOCK_END

; EXECUTABLE_BLOCK_START
M73 P0 R15
M201 X20000 Y20000 Z500 E5000
M203 X1000 Y1000 Z30 E50
M204 P20000 R5000 T20000
M205 X9.00 Y9.00 Z3.00 E2.50
M106 S0
M106 P2 S0
M190 S70 ; set bed temperature and wait for it to be reached
; FEATURE: Custom
G0 Z20 F9000
G92 E0; G1 E-10 F1200
G28
M970 Q1 A10 B10 C130 K0
M970 Q1 A10 B131 C250 K1
M974 Q1 S1 P0
M970 Q0 A10 B10 C130 H20 K0
M970 Q0 A10 B131 C250 K1
M974 Q0 S1 P0
M220 S100 ;Reset Feedrate
M221 S100 ;Reset Flowrate
G29 ;Home
G90;
G92 E0 ;Reset Extruder 
G1 Z2.0 F3000 ;Move Z Axis up 
G1 X10.1 Y20 Z0.28 F5000.0 ;Move to start position
M109 S205;
G1 X10.1 Y200.0 Z0.28 F1500.0 E15 ;Draw the first line
G1 X10.4 Y200.0 Z0.28 F5000.0 ;Move to side a little
G1 X10.4 Y20 Z0.28 F1500.0 E30 ;Draw the second line
G92 E0 ;Reset Extruder 
G1 X110 Y110 Z2.0 F3000 ;Move Z Axis up
; MACHINE_START_GCODE_END
; filament start gcode
;VT0 H-1
G90
G21
M83 ; use relative distances for extrusion
M981 S1 P20000 ;open spaghetti detector
; CHANGE_LAYER
; Z_HEIGHT: 0.2
; LAYER_HEIGHT: 0.2
G1 E-.4 F1800
; layer num/total_layer_count: 1/27
; update layer progress
M73 L1
M991 S0 P0 ;notify layer change
M106 S0
M106 P2 S0
; OBJECT_ID: 16
; start printing object, unique label id: 16
M624 BAAAAAAAAAA=
M73 P1 R15
G1 X194.981 Y178.762 F60000
M204 S6000
M73 P2 R15
G1 Z.4
G1 Z.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.5
G1 F3000
M204 S500
G1 X194.719 Y178.752 E.00947
G3 X194.531 Y171.256 I.281 J-3.757 E.40026
G1 X194.906 Y171.228 E.01359
G3 X195.281 Y178.752 I.094 J3.767 E.4206
G1 X195.041 Y178.76 E.00865
M204 S6000
G1 X194.979 Y178.306 F60000
G1 F3000
M204 S500
G1 X194.753 Y178.297 E.00818
G3 X194.588 Y171.71 I.247 J-3.302 E.35172
G1 X194.917 Y171.685 E.01194
G3 X195.247 Y178.297 I.082 J3.31 E.3696
G1 X195.039 Y178.304 E.00749
M204 S6000
G1 X194.978 Y177.85 F60000
G1 F3000
M204 S500
G1 X194.787 Y177.842 E.0069
G3 X194.644 Y172.164 I.213 J-2.846 E.30318
G1 X194.929 Y172.143 E.01029
G3 X195.213 Y177.842 I.071 J2.853 E.31859
G1 X195.038 Y177.848 E.00631
M204 S6000
G1 X194.977 Y177.394 F60000
; FEATURE: Outer wall
G1 F3000
M204 S500
G1 X194.821 Y177.387 E.00563
G3 X194.701 Y172.618 I.179 J-2.39 E.25464
G1 X194.94 Y172.6 E.00864
G3 X195.179 Y177.387 I.06 J2.396 E.26758
G1 X195.037 Y177.392 E.00512
; WIPE_START
G1 X194.821 Y177.387 E-.08202
G1 X194.35 Y177.311 E-.18136
G1 X194.064 Y177.199 E-.11661
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-1.067 J.585 P1  F60000
G1 X202.6 Y192.771 Z.6
G1 Z.2
G1 E.4 F1800
; FEATURE: Inner wall
G1 F3000
M204 S500
G1 X204.729 Y192.771 E.07686
G1 X204.729 Y200.914 E.29401
G2 X200.419 Y199.965 I-2.735 J2.158 E.17256
G2 X199.65 Y200.514 I1.754 J3.27 E.03421
G2 X190.35 Y200.513 I-4.65 J2.492 E.41101
G2 X185.61 Y200.549 I-2.351 J2.522 E.18871
G1 X185.271 Y200.914 E.01796
G1 X185.271 Y192.771 E.29401
G1 X188.771 Y192.771 E.12637
G1 X188.771 Y170.771 E.79433
G1 X201.229 Y170.771 E.44979
G1 X201.229 Y192.771 E.79433
G1 X202.54 Y192.771 E.04734
M204 S6000
G1 X202.6 Y192.314 F60000
G1 F3000
M204 S500
G1 X205.186 Y192.314 E.09337
G1 X205.186 Y202.56 E.36995
G1 X204.932 Y202.579 E.00919
G2 X199.524 Y201.352 I-2.943 J.436 E.25786
G2 X190.473 Y201.359 I-4.524 J1.651 E.42484
G2 X185.068 Y202.579 I-2.467 J1.653 E.25789
G1 X184.814 Y202.56 E.00919
G1 X184.814 Y192.314 E.36995
G1 X188.314 Y192.314 E.12637
G1 X188.314 Y170.314 E.79433
G1 X201.686 Y170.314 E.4828
G1 X201.686 Y192.314 E.79433
G1 X202.54 Y192.314 E.03084
M204 S6000
G1 X202.6 Y191.857 F60000
G1 F3000
M204 S500
G1 X205.643 Y191.857 E.10987
G1 X205.643 Y210.143 E.66023
G1 X204.757 Y210.143 E.03199
G1 X204.757 Y209.143 E.03611
G1 X204.507 Y209.143 E.00903
M73 P3 R15
G1 X204.507 Y202.978 E.22257
G2 X199.551 Y202.465 I-2.508 J.029 E.26366
G1 X199.328 Y202.458 E.00807
G2 X190.673 Y202.455 I-4.328 J.548 E.45501
G1 X190.457 Y202.468 E.0078
G2 X185.493 Y202.979 I-2.453 J.538 E.26433
G1 X185.493 Y209.143 E.22256
G1 X185.243 Y209.143 E.00903
G1 X185.243 Y210.143 E.03611
G1 X184.357 Y210.143 E.03199
G1 X184.357 Y191.857 E.66023
G1 X187.857 Y191.857 E.12637
G1 X187.857 Y169.857 E.79433
G1 X202.143 Y169.857 E.51581
G1 X202.143 Y191.857 E.79433
G1 X202.54 Y191.857 E.01434
M204 S6000
G1 X202.6 Y191.4 F60000
; FEATURE: Outer wall
G1 F3000
M204 S500
G1 X206.1 Y191.4 E.12637
G1 X206.1 Y210.6 E.69324
; object ids of layer 1 start: 8,12,16
M624 BwAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer1 end: 8,12,16
M625
G1 X204.3 Y210.6 E.06499
G1 X204.3 Y209.6 E.03611
G1 X204.05 Y209.6 E.00903
G1 X204.05 Y202.99 E.23867
G2 X199.95 Y202.99 I-2.05 J.016 E.23142
G1 X199.95 Y209.6 E.23865
G1 X199.7 Y209.6 E.00903
G1 X199.7 Y210.6 E.03611
G1 X198.9 Y210.6 E.02889
G1 X198.9 Y202.995 E.27459
G2 X191.1 Y202.994 I-3.9 J.006 E.44189
G1 X191.1 Y210.6 E.27463
G1 X190.3 Y210.6 E.02889
M73 P3 R14
G1 X190.3 Y209.6 E.03611
G1 X190.05 Y209.6 E.00903
G1 X190.05 Y202.99 E.23867
G2 X185.95 Y202.99 I-2.05 J.016 E.23142
G1 X185.95 Y209.6 E.23865
G1 X185.7 Y209.6 E.00903
G1 X185.7 Y210.6 E.03611
G1 X183.9 Y210.6 E.06499
G1 X183.9 Y191.4 E.69324
G1 X187.4 Y191.4 E.12637
G1 X187.4 Y169.4 E.79433
G1 X202.6 Y169.4 E.54881
G1 X202.6 Y191.34 E.79217
; WIPE_START
G1 X203.6 Y191.357 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-1.212 J.104 P1  F60000
G1 X204.36 Y200.182 Z.6
G1 Z.2
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.112263
G1 F3000
M204 S500
G1 X204.5 Y200.283 E.00094
; WIPE_START
G1 X204.36 Y200.182 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-1.155 J.384 P1  F60000
G1 X204.729 Y201.29 Z.6
G1 Z.2
G1 E.4 F1800
; LINE_WIDTH: 0.11732
G1 F3000
M204 S500
G1 X204.859 Y201.468 E.0013
; LINE_WIDTH: 0.150124
G1 X204.957 Y201.605 E.00142
M204 S6000
G1 X204.933 Y201.683 F60000
; LINE_WIDTH: 0.122577
G1 F3000
M204 S500
G2 X204.872 Y201.404 I-5.453 J1.058 E.00179
; WIPE_START
G1 X204.933 Y201.683 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-1.207 J.153 P1  F60000
G1 X205.075 Y202.798 Z.6
G1 Z.2
G1 E.4 F1800
; LINE_WIDTH: 0.721522
G1 F3000
M204 S500
G1 X205.075 Y208.587 E.31032
G1 X205.096 Y208.642 E.00313
; LINE_WIDTH: 0.659235
G1 X205.117 Y208.696 E.00284
; LINE_WIDTH: 0.617565
G1 X205.138 Y208.751 E.00265
; LINE_WIDTH: 0.575895
G1 X205.158 Y208.805 E.00246
; LINE_WIDTH: 0.534225
G1 X205.179 Y208.86 E.00227
; LINE_WIDTH: 0.492555
G1 X205.2 Y208.914 E.00207
; LINE_WIDTH: 0.47174
G1 X205.2 Y209.914 E.03387
; WIPE_START
G1 X205.2 Y208.914 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-.097 J-1.213 P1  F60000
G1 X199.721 Y209.352 Z.6
M73 P4 R14
G1 Z.2
G1 E.4 F1800
; LINE_WIDTH: 0.566155
G1 F3000
M204 S500
G1 X199.573 Y209.215 E.00833
; LINE_WIDTH: 0.612625
G1 X199.425 Y209.079 E.00907
; LINE_WIDTH: 0.634713
G2 X199.425 Y202.986 I-562.521 J-3.043 E.2848
G1 X199.729 Y202.698 E.01957
M204 S6000
G1 X199.473 Y201.903 F60000
; LINE_WIDTH: 0.111987
G1 F3000
M204 S500
G3 X199.503 Y201.799 I.119 J-.022 E.00061
G1 X199.544 Y201.737 E.00041
; WIPE_START
G1 X199.503 Y201.799 E-.15362
G1 X199.478 Y201.841 E-.09879
G1 X199.473 Y201.903 E-.1276
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-1.216 J.047 P1  F60000
G1 X199.721 Y208.384 Z.6
G1 Z.2
G1 E.4 F1800
; LINE_WIDTH: 0.610871
G1 F3000
M204 S500
G1 X199.637 Y208.582 E.00963
; LINE_WIDTH: 0.560873
G1 X199.553 Y208.779 E.00878
; LINE_WIDTH: 0.510875
G1 X199.469 Y208.977 E.00794
; LINE_WIDTH: 0.460877
G1 X199.384 Y209.174 E.00709
; LINE_WIDTH: 0.410879
G1 X199.3 Y209.371 E.00624
; LINE_WIDTH: 0.38586
G1 X199.3 Y210.371 E.02709
; WIPE_START
G1 X199.3 Y209.371 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-.141 J-1.209 P1  F60000
G1 X190.7 Y210.371 Z.6
G1 Z.2
G1 E.4 F1800
; LINE_WIDTH: 0.38692
G1 F3000
M204 S500
G1 X190.7 Y209.371 E.02717
G1 X190.679 Y209.323 E.00144
; LINE_WIDTH: 0.448365
G1 X190.658 Y209.274 E.0017
; LINE_WIDTH: 0.490035
G1 X190.637 Y209.225 E.00187
; LINE_WIDTH: 0.531705
G1 X190.617 Y209.176 E.00205
; LINE_WIDTH: 0.573375
G1 X190.596 Y209.127 E.00222
; LINE_WIDTH: 0.615045
G1 X190.575 Y209.079 E.0024
; LINE_WIDTH: 0.635515
G1 X190.575 Y202.987 E.28515
G1 X190.878 Y202.671 E.0205
; WIPE_START
G1 X190.575 Y202.987 E-.16639
G1 X190.575 Y203.549 E-.21361
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I.476 J-1.12 P1  F60000
G1 X185.265 Y201.295 Z.6
G1 Z.2
G1 E.4 F1800
; LINE_WIDTH: 0.11831
G1 F3000
M204 S500
G1 X185.154 Y201.45 E.00114
; LINE_WIDTH: 0.14909
G1 X185.043 Y201.605 E.0016
M204 S6000
G1 X185.067 Y201.683 F60000
; LINE_WIDTH: 0.122519
G1 F3000
M204 S500
G3 X185.128 Y201.405 I5.44 J1.055 E.00179
; WIPE_START
G1 X185.067 Y201.683 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I1.163 J.36 P1  F60000
G1 X185.5 Y200.283 Z.6
G1 Z.2
G1 E.4 F1800
; LINE_WIDTH: 0.112262
G1 F3000
M204 S500
G1 X185.64 Y200.182 E.00094
; WIPE_START
G1 X185.5 Y200.283 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-1.186 J-.271 P1  F60000
G1 X184.925 Y202.798 Z.6
G1 Z.2
G1 E.4 F1800
; LINE_WIDTH: 0.721315
G1 F3000
M204 S500
G1 X184.925 Y208.587 E.31023
G1 X185.01 Y208.66 E.00601
; LINE_WIDTH: 0.65467
G1 X185.095 Y208.734 E.00542
; LINE_WIDTH: 0.60997
G1 X185.18 Y208.807 E.00503
; LINE_WIDTH: 0.56527
G1 X185.264 Y208.881 E.00463
; WIPE_START
G1 X185.18 Y208.807 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I1.193 J.239 P1  F60000
G1 X192.594 Y171.865 Z.6
G1 Z.2
G1 E.4 F1800
; FEATURE: Bottom surface
; LINE_WIDTH: 0.50174
G1 F6300
M204 S500
G1 X191.889 Y171.16 E.03614
G1 X191.24 Y171.16 E.02352
G1 X192.101 Y172.021 E.04413
G2 X191.79 Y172.358 I1.533 J1.724 E.01667
G1 X190.591 Y171.16 E.06144
G1 X189.942 Y171.16 E.02352
G1 X191.52 Y172.738 E.0809
G2 X191.279 Y173.145 I1.566 J1.204 E.01721
G1 X189.293 Y171.16 E.10178
G1 X189.16 Y171.16 E.00484
G1 X189.16 Y171.675 E.01868
G1 X191.085 Y173.601 E.0987
G2 X190.939 Y174.103 I2.432 J.983 E.01899
G1 X189.16 Y172.324 E.09118
G1 X189.16 Y172.973 E.02352
G1 X190.854 Y174.667 E.08685
G2 X190.853 Y175.315 I3.231 J.328 E.02353
G1 X189.16 Y173.622 E.08681
G1 X189.16 Y174.271 E.02352
G1 X191.313 Y176.424 E.11038
; WIPE_START
G1 X190.606 Y175.717 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I.545 J1.088 P1  F60000
G1 X200.118 Y170.954 Z.6
G1 Z.2
G1 E.4 F1800
G1 F6300
M204 S500
G1 X200.84 Y171.676 E.03701
G1 X200.84 Y172.325 E.02352
G1 X199.675 Y171.16 E.05972
G1 X199.026 Y171.16 E.02352
G1 X200.84 Y172.974 E.09298
G1 X200.84 Y173.623 E.02352
G1 X198.377 Y171.16 E.12624
G1 X197.729 Y171.16 E.02352
G1 X200.84 Y174.271 E.1595
G1 X200.84 Y174.92 E.02352
G1 X197.42 Y171.5 E.17532
G1 X197.4 Y171.605 E.00389
G3 X198.939 Y173.668 I-2.409 J3.403 E.09484
G1 X200.84 Y175.569 E.09743
G1 X200.84 Y176.218 E.02352
G1 X199.13 Y174.508 E.08766
G3 X199.153 Y175.18 I-4.533 J.495 E.0244
G1 X200.84 Y176.867 E.08646
G1 X200.84 Y177.516 E.02352
G1 X199.081 Y175.756 E.09019
G3 X198.956 Y176.28 I-2.235 J-.256 E.01957
G1 X200.84 Y178.165 E.0966
G1 X200.84 Y178.814 E.02352
G1 X198.775 Y176.748 E.10588
G3 X198.55 Y177.172 I-8.765 J-4.36 E.0174
G1 X200.84 Y179.462 E.11737
G1 X200.84 Y180.111 E.02352
G1 X198.283 Y177.554 E.13105
G3 X197.98 Y177.9 I-1.877 J-1.339 E.01669
G1 X200.84 Y180.76 E.14659
G1 X200.84 Y181.409 E.02352
G1 X197.642 Y178.211 E.16394
G3 X197.265 Y178.483 I-1.55 J-1.744 E.01687
G1 X200.84 Y182.058 E.18323
G1 X200.84 Y182.707 E.02352
G1 X196.854 Y178.721 E.2043
G3 X196.401 Y178.916 I-1.204 J-2.173 E.01793
G1 X200.84 Y183.356 E.22755
G1 X200.84 Y184.005 E.02352
G1 X195.899 Y179.063 E.25329
G3 X195.329 Y179.142 I-.681 J-2.811 E.02088
G1 X200.84 Y184.653 E.28249
G1 X200.84 Y185.302 E.02352
G1 X194.689 Y179.151 E.3153
G3 X193.903 Y179.014 I.292 J-3.998 E.02896
G1 X200.84 Y185.951 E.35558
G1 X200.84 Y186.6 E.02352
G1 X189.16 Y174.919 E.5987
G1 X189.16 Y175.568 E.02352
G1 X200.84 Y187.249 E.5987
G1 X200.84 Y187.898 E.02352
G1 X189.16 Y176.217 E.5987
M73 P5 R14
G1 X189.16 Y176.866 E.02352
G1 X200.84 Y188.547 E.5987
G1 X200.84 Y189.196 E.02352
G1 X189.16 Y177.515 E.5987
G1 X189.16 Y178.164 E.02352
G1 X200.84 Y189.844 E.5987
G1 X200.84 Y190.493 E.02352
G1 X189.16 Y178.813 E.5987
G1 X189.16 Y179.462 E.02352
G1 X200.84 Y191.142 E.5987
G1 X200.84 Y191.791 E.02352
G1 X189.16 Y180.11 E.5987
G1 X189.16 Y180.759 E.02352
G1 X201.046 Y192.646 E.60924
; WIPE_START
G1 X200.339 Y191.938 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-.329 J1.172 P1  F60000
G1 X203.95 Y192.954 Z.6
G1 Z.2
G1 E.4 F1800
G1 F6300
M204 S500
G1 X204.34 Y193.344 E.02001
G1 X204.34 Y193.993 E.02352
G1 X203.507 Y193.16 E.04272
G1 X202.858 Y193.16 E.02352
G1 X204.34 Y194.642 E.07598
G1 X204.34 Y195.291 E.02352
G1 X202.209 Y193.16 E.10924
G1 X201.56 Y193.16 E.02352
G1 X204.34 Y195.94 E.1425
G1 X204.34 Y196.589 E.02352
G1 X189.16 Y181.408 E.7781
G1 X189.16 Y182.057 E.02352
G1 X204.34 Y197.238 E.7781
G1 X204.34 Y197.886 E.02352
G1 X189.16 Y182.706 E.7781
G1 X189.16 Y183.355 E.02352
G1 X204.34 Y198.535 E.7781
G1 X204.34 Y199.184 E.02352
G1 X189.16 Y184.004 E.7781
G1 X189.16 Y184.652 E.02352
G1 X204.22 Y199.712 E.77191
G1 X204.128 Y199.84 E.0057
G2 X203.271 Y199.412 I-1.718 J2.37 E.03486
G1 X189.16 Y185.301 E.72328
G1 X189.16 Y185.95 E.02352
G1 X202.425 Y199.216 E.67994
G1 X201.758 Y199.198 E.02418
G1 X189.16 Y186.599 E.64576
G1 X189.16 Y187.248 E.02352
G1 X201.195 Y199.283 E.61689
G2 X200.688 Y199.425 I.286 J2.011 E.01915
G1 X189.16 Y187.897 E.59087
G1 X189.16 Y188.546 E.02352
G1 X200.243 Y199.629 E.56809
G2 X199.833 Y199.868 I.711 J1.69 E.01724
G1 X189.16 Y189.195 E.54709
G1 X189.16 Y189.843 E.02352
G1 X197.036 Y197.72 E.40371
M73 P6 R14
G2 X196.121 Y197.453 I-2.049 J5.336 E.03459
G1 X189.16 Y190.492 E.3568
G1 X189.16 Y191.141 E.02352
G1 X195.374 Y197.356 E.31853
G2 X194.721 Y197.351 I-.348 J3.166 E.02372
G1 X189.16 Y191.79 E.28505
G1 X189.16 Y192.439 E.02352
G1 X194.129 Y197.409 E.25473
G2 X193.594 Y197.522 I.485 J3.62 E.01986
G1 X189.16 Y193.088 E.22727
G1 X189.16 Y193.16 E.00261
G1 X188.583 Y193.16 E.02091
G1 X193.098 Y197.675 E.23142
G2 X192.633 Y197.859 I1.543 J4.565 E.01812
G1 X187.934 Y193.16 E.24087
G1 X187.285 Y193.16 E.02352
G1 X192.209 Y198.083 E.25236
G2 X191.806 Y198.329 I1.443 J2.817 E.01712
G1 X186.636 Y193.16 E.26497
G1 X185.987 Y193.16 E.02352
G1 X191.437 Y198.61 E.27935
G2 X191.092 Y198.914 I1.348 J1.877 E.01669
G1 X185.66 Y193.481 E.27846
G1 X185.66 Y194.13 E.02352
G1 X190.771 Y199.241 E.26196
G2 X190.482 Y199.601 I2.259 J2.104 E.01675
G1 X185.66 Y194.779 E.24717
G1 X185.66 Y195.428 E.02352
G1 X189.976 Y199.744 E.22126
G1 X189.735 Y199.605 E.01012
G1 X189.214 Y199.387 E.02046
G1 X188.886 Y199.303 E.01227
G1 X185.66 Y196.076 E.16535
G1 X185.66 Y196.725 E.02352
G1 X188.134 Y199.2 E.12682
G2 X187.51 Y199.224 I-.219 J2.401 E.02271
G1 X185.66 Y197.374 E.09481
G1 X185.66 Y198.023 E.02352
G1 X186.975 Y199.338 E.06741
G2 X186.497 Y199.509 I.29 J1.567 E.01848
G1 X185.66 Y198.672 E.0429
G1 X185.66 Y199.321 E.02352
G1 X186.212 Y199.873 E.02831
; WIPE_START
G1 X185.66 Y199.321 E-.29679
G1 X185.66 Y199.102 E-.08321
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I1.177 J.308 P1  F60000
G1 X192.936 Y171.258 Z.6
G1 Z.2
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.406613
G1 F3000
M204 S500
G3 X193.387 Y171.163 I2.083 J8.802 E.01326
; LINE_WIDTH: 0.35109
G1 X193.487 Y171.144 E.00247
; LINE_WIDTH: 0.313376
G1 X193.586 Y171.126 E.00217
; LINE_WIDTH: 0.275662
G1 X193.686 Y171.107 E.00186
; LINE_WIDTH: 0.236469
G1 X193.83 Y171.087 E.00222
; LINE_WIDTH: 0.198274
G1 X193.963 Y171.068 E.00165
; LINE_WIDTH: 0.161564
G1 X194.096 Y171.05 E.00126
; LINE_WIDTH: 0.122896
G1 X194.354 Y171.027 E.00164
; WIPE_START
G1 X194.096 Y171.05 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I.018 J1.217 P1  F60000
G1 X195.674 Y171.026 Z.6
G1 Z.2
G1 E.4 F1800
; LINE_WIDTH: 0.125303
G1 F3000
M204 S500
G1 X195.887 Y171.05 E.0014
; LINE_WIDTH: 0.170068
G1 X196.101 Y171.074 E.00216
; LINE_WIDTH: 0.215042
G1 X196.241 Y171.097 E.00193
; LINE_WIDTH: 0.25972
G1 X196.374 Y171.119 E.00231
; LINE_WIDTH: 0.303187
G1 X196.507 Y171.141 E.00277
; LINE_WIDTH: 0.327607
G1 X197.072 Y171.248 E.01294
; OBJECT_ID: 12
; WIPE_START
G1 X196.507 Y171.141 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 16
M625
; start printing object, unique label id: 12
M624 AgAAAAAAAAA=
M204 S6000
G17
G3 Z.6 I1.217 J.027 P1  F60000
G1 X197.694 Y117.637 Z.6
G1 Z.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.5
G1 F3000
M204 S500
G1 X197.498 Y117.831 E.00994
G3 X194.718 Y111.239 I-2.491 J-2.832 E.51563
G3 X195.655 Y111.284 I.261 J4.337 E.03394
G3 X197.768 Y117.568 I-.649 J3.715 E.29241
G1 X197.737 Y117.596 E.00149
M204 S6000
G1 X197.374 Y117.31 F60000
G1 F3000
M204 S500
G1 X197.195 Y117.488 E.00911
G3 X194.752 Y111.695 I-2.188 J-2.489 E.45299
G1 X194.934 Y111.686 E.00656
G3 X197.432 Y117.257 I.073 J3.313 E.2803
G1 X197.419 Y117.27 E.00067
M204 S6000
G1 X197.055 Y116.983 F60000
G1 F3000
M204 S500
G1 X196.892 Y117.144 E.00829
G3 X194.787 Y112.151 I-1.887 J-2.145 E.3906
G1 X194.94 Y112.143 E.00553
G3 X197.099 Y116.942 I.065 J2.856 E.2415
M204 S6000
G1 X196.73 Y116.659 F60000
; FEATURE: Outer wall
G1 F3000
M204 S500
G1 X196.401 Y116.948 E.01581
G3 X194.821 Y112.607 I-1.399 J-1.949 E.31954
G1 X194.945 Y112.6 E.0045
G3 X196.773 Y116.618 I.057 J2.399 E.20228
; WIPE_START
G1 X196.401 Y116.948 E-.18911
G1 X195.987 Y117.188 E-.1816
G1 X195.964 Y117.196 E-.00929
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-1.12 J.477 P1  F60000
G1 X202.6 Y132.771 Z.6
G1 Z.2
G1 E.4 F1800
; FEATURE: Inner wall
G1 F3000
M204 S500
G1 X204.729 Y132.771 E.07686
G1 X204.729 Y140.914 E.294
G2 X200.017 Y140.21 I-2.729 J2.146 E.18956
G2 X199.65 Y140.514 I1.953 J2.736 E.01721
G2 X190.353 Y140.508 I-4.65 J2.492 E.41077
G2 X185.611 Y140.548 I-2.35 J2.515 E.1889
G1 X185.271 Y140.914 E.01801
G1 X185.271 Y132.771 E.294
M73 P7 R14
G1 X188.771 Y132.771 E.12637
G1 X188.771 Y110.771 E.79433
G1 X201.229 Y110.771 E.44979
G1 X201.229 Y132.771 E.79433
G1 X202.54 Y132.771 E.04734
M204 S6000
G1 X202.6 Y132.314 F60000
G1 F3000
M204 S500
G1 X205.186 Y132.314 E.09337
G1 X205.186 Y142.561 E.36997
G1 X204.932 Y142.58 E.00918
G2 X199.527 Y141.359 I-2.936 J.421 E.25833
G2 X190.479 Y141.345 I-4.526 J1.643 E.42458
G2 X187.516 Y140.075 I-2.508 J1.761 E.12257
G2 X185.068 Y142.58 I.49 J2.928 E.13527
G1 X184.814 Y142.561 E.00918
G1 X184.814 Y132.314 E.36997
G1 X188.314 Y132.314 E.12637
G1 X188.314 Y110.314 E.79433
G1 X201.686 Y110.314 E.4828
G1 X201.686 Y132.314 E.79433
G1 X202.54 Y132.314 E.03084
; WIPE_START
G1 X203.54 Y132.314 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-1.21 J.126 P1  F60000
G1 X204.764 Y144.068 Z.6
G1 Z.2
G1 E.4 F1800
G1 F3000
M204 S500
G2 X204.939 Y143.411 I-3.261 J-1.218 E.0246
G1 X205.186 Y143.435 E.00896
G1 X205.186 Y148.686 E.18958
G1 X204.764 Y148.686 E.01523
G1 X204.764 Y144.128 E.16456
; WIPE_START
G1 X204.875 Y143.729 E-.15743
G1 X204.939 Y143.411 E-.12336
G1 X205.186 Y143.435 E-.09434
G1 X205.186 Y143.448 E-.00487
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-.309 J-1.177 P1  F60000
G1 X185.236 Y148.686 Z.6
G1 Z.2
G1 E.4 F1800
G1 F3000
M204 S500
G1 X184.814 Y148.686 E.01523
G1 X184.814 Y143.435 E.18958
G1 X185.061 Y143.411 E.00896
G1 X185.125 Y143.729 E.01172
G2 X185.236 Y144.069 I2.164 J-.517 E.01292
G1 X185.236 Y148.626 E.16454
; WIPE_START
G1 X184.814 Y148.686 E-.16187
G1 X184.814 Y148.112 E-.21813
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I.821 J.898 P1  F60000
G1 X202.6 Y131.857 Z.6
G1 Z.2
G1 E.4 F1800
G1 F3000
M204 S500
G1 X205.643 Y131.857 E.10987
G1 X205.643 Y150.143 E.66023
G1 X204.757 Y150.143 E.03199
G1 X204.757 Y149.143 E.03611
G1 X204.307 Y149.143 E.01625
G1 X204.307 Y143.976 E.18656
G2 X199.543 Y142.468 I-2.314 J-.97 E.30094
G1 X199.327 Y142.455 E.0078
G2 X190.672 Y142.463 I-4.327 J.551 E.45517
G1 X190.45 Y142.471 E.00799
G2 X185.693 Y143.981 I-2.451 J.529 E.30154
G1 X185.693 Y149.143 E.18637
G1 X185.243 Y149.143 E.01625
G1 X185.243 Y150.143 E.03611
G1 X184.357 Y150.143 E.03199
G1 X184.357 Y131.857 E.66023
G1 X187.857 Y131.857 E.12637
G1 X187.857 Y109.857 E.79433
G1 X202.143 Y109.857 E.51581
G1 X202.143 Y131.857 E.79433
M73 P8 R14
G1 X202.54 Y131.857 E.01434
; WIPE_START
G1 X203.54 Y131.857 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-1.161 J-.366 P1  F60000
G1 X199.693 Y144.05 Z.6
G1 Z.2
G1 E.4 F1800
G1 F3000
M204 S500
G1 X199.693 Y149.143 E.18387
G1 X199.357 Y149.143 E.01213
G1 X199.357 Y143.722 E.19572
G1 X199.591 Y143.687 E.00853
G1 X199.64 Y143.847 E.00604
G1 X199.693 Y143.981 E.0052
G1 X199.693 Y143.99 E.00033
; WIPE_START
G1 X199.693 Y144.99 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-.448 J-1.132 P1  F60000
G1 X190.643 Y148.57 Z.6
G1 Z.2
G1 E.4 F1800
G1 F3000
M204 S500
G1 X190.643 Y149.143 E.02069
G1 X190.307 Y149.143 E.01213
G1 X190.307 Y143.976 E.18656
G2 X190.409 Y143.687 I-1.386 J-.654 E.01108
G1 X190.643 Y143.722 E.00853
G1 X190.643 Y148.51 E.17286
; WIPE_START
G1 X190.643 Y149.143 E-.24056
G1 X190.307 Y149.143 E-.12763
G1 X190.307 Y149.112 E-.01181
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I1 J.694 P1  F60000
G1 X202.6 Y131.4 Z.6
G1 Z.2
G1 E.4 F1800
; FEATURE: Outer wall
G1 F3000
M204 S500
G1 X206.1 Y131.4 E.12637
G1 X206.1 Y150.6 E.69324
G1 X204.3 Y150.6 E.06499
G1 X204.3 Y149.6 E.03611
G1 X203.85 Y149.6 E.01625
G1 X203.85 Y143.883 E.20642
G2 X200.15 Y143.879 I-1.849 J-.882 E.29809
G1 X200.15 Y149.6 E.20657
G1 X199.7 Y149.6 E.01625
G1 X199.7 Y150.6 E.03611
G1 X198.9 Y150.6 E.02889
G1 X198.9 Y142.995 E.27459
G2 X191.1 Y142.994 I-3.9 J.006 E.44189
G1 X191.1 Y150.6 E.27463
G1 X190.3 Y150.6 E.02889
G1 X190.3 Y149.6 E.03611
G1 X189.85 Y149.6 E.01625
G1 X189.85 Y143.883 E.20642
G2 X186.15 Y143.879 I-1.849 J-.882 E.29808
G1 X186.15 Y149.6 E.20657
G1 X185.7 Y149.6 E.01625
G1 X185.7 Y150.6 E.03611
G1 X183.9 Y150.6 E.06499
G1 X183.9 Y131.4 E.69324
G1 X187.4 Y131.4 E.12637
G1 X187.4 Y109.4 E.79433
G1 X202.6 Y109.4 E.54881
G1 X202.6 Y131.34 E.79217
; WIPE_START
G1 X203.6 Y131.357 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-1.209 J.138 P1  F60000
G1 X204.733 Y141.293 Z.6
G1 Z.2
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.118382
G1 F3000
M204 S500
G1 X204.815 Y141.407 E.00083
; LINE_WIDTH: 0.149326
G1 X204.896 Y141.52 E.00117
; LINE_WIDTH: 0.14032
G3 X204.936 Y141.682 I-3.92 J1.03 E.00129
; WIPE_START
G1 X204.896 Y141.52 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-1.216 J.05 P1  F60000
G1 X205.2 Y148.915 Z.6
G1 Z.2
G1 E.4 F1800
; LINE_WIDTH: 0.47173
G1 F3000
M204 S500
G1 X205.2 Y149.914 E.03387
; WIPE_START
G1 X205.2 Y148.915 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-.292 J-1.181 P1  F60000
G1 X199.3 Y150.371 Z.6
G1 Z.2
G1 E.4 F1800
; LINE_WIDTH: 0.38587
G1 F3000
M204 S500
G1 X199.3 Y149.372 E.02709
; WIPE_START
G1 X199.3 Y150.371 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I.141 J-1.209 P1  F60000
G1 X190.7 Y149.372 Z.6
G1 Z.2
G1 E.4 F1800
G1 F3000
M204 S500
G1 X190.7 Y150.371 E.02709
; WIPE_START
G1 X190.7 Y149.372 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-.111 J-1.212 P1  F60000
G1 X184.8 Y149.914 Z.6
G1 Z.2
M73 P9 R14
G1 E.4 F1800
; LINE_WIDTH: 0.47173
G1 F3000
M204 S500
G1 X184.8 Y148.915 E.03387
; WIPE_START
G1 X184.8 Y149.914 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I1.216 J.039 P1  F60000
G1 X185.064 Y141.682 Z.6
G1 Z.2
G1 E.4 F1800
; LINE_WIDTH: 0.144433
G1 F3000
M204 S500
G3 X185.17 Y141.427 I.446 J.035 E.00225
; LINE_WIDTH: 0.122131
G1 X185.237 Y141.334 E.00072
; LINE_WIDTH: 0.105264
G1 X185.273 Y141.288 E.00029
; WIPE_START
G1 X185.237 Y141.334 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-.08 J1.214 P1  F60000
G1 X190.426 Y141.678 Z.6
G1 Z.2
G1 E.4 F1800
; LINE_WIDTH: 0.120848
G1 F3000
M204 S500
G1 X190.52 Y141.822 E.00106
G1 X190.527 Y141.902 E.00049
; WIPE_START
G1 X190.52 Y141.822 E-.12103
G1 X190.426 Y141.678 E-.25897
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I1.213 J.1 P1  F60000
G1 X192.936 Y111.258 Z.6
G1 Z.2
G1 E.4 F1800
; LINE_WIDTH: 0.406628
G1 F3000
M204 S500
G3 X193.387 Y111.163 I2.125 J9.019 E.01326
; LINE_WIDTH: 0.351117
G1 X193.487 Y111.144 E.00247
; LINE_WIDTH: 0.313395
G1 X193.586 Y111.126 E.00217
; LINE_WIDTH: 0.275673
G1 X193.686 Y111.107 E.00186
; LINE_WIDTH: 0.236486
G1 X193.83 Y111.087 E.00222
; LINE_WIDTH: 0.198284
G1 X193.963 Y111.068 E.00165
; LINE_WIDTH: 0.161567
G1 X194.096 Y111.05 E.00126
; LINE_WIDTH: 0.122886
G1 X194.354 Y111.027 E.00164
; WIPE_START
G1 X194.096 Y111.05 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I.018 J1.217 P1  F60000
G1 X195.674 Y111.026 Z.6
G1 Z.2
G1 E.4 F1800
; LINE_WIDTH: 0.125298
G1 F3000
M204 S500
G1 X195.887 Y111.05 E.0014
; LINE_WIDTH: 0.170054
G1 X196.101 Y111.074 E.00216
; LINE_WIDTH: 0.215013
G1 X196.241 Y111.097 E.00193
; LINE_WIDTH: 0.259666
G1 X196.374 Y111.119 E.00231
; LINE_WIDTH: 0.30311
G1 X196.507 Y111.141 E.00277
; LINE_WIDTH: 0.327504
G1 X197.072 Y111.248 E.01294
; WIPE_START
G1 X196.507 Y111.141 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I.063 J1.215 P1  F60000
G1 X200.109 Y110.954 Z.6
G1 Z.2
G1 E.4 F1800
; FEATURE: Bottom surface
; LINE_WIDTH: 0.50612
G1 F6300
M204 S500
G1 X200.84 Y111.685 E.03784
G1 X200.84 Y112.34 E.02397
G1 X199.66 Y111.16 E.06109
G1 X199.005 Y111.16 E.02397
G1 X200.84 Y112.995 E.09499
G1 X200.84 Y113.65 E.02397
G1 X198.35 Y111.16 E.12889
G1 X197.694 Y111.16 E.02397
G1 X200.84 Y114.306 E.16278
G1 X200.84 Y114.961 E.02397
G1 X197.237 Y111.358 E.18643
; WIPE_START
G1 X197.944 Y112.065 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-1.087 J.547 P1  F60000
G1 X198.607 Y113.382 Z.6
G1 Z.2
G1 E.4 F1800
G1 F6300
M204 S500
G1 X200.84 Y115.616 E.11557
G1 X200.84 Y116.271 E.02397
G1 X199.139 Y114.57 E.08802
G3 X199.145 Y115.23 I-4.427 J.366 E.02419
G1 X200.84 Y116.926 E.08774
G1 X200.84 Y117.581 E.02397
G1 X199.076 Y115.817 E.09128
G3 X198.939 Y116.335 I-2.661 J-.429 E.01963
G1 X200.84 Y118.236 E.09839
G1 X200.84 Y118.891 E.02397
G1 X198.752 Y116.802 E.10807
G3 X198.516 Y117.222 I-8.529 J-4.505 E.01761
G1 X200.84 Y119.546 E.12025
G1 X200.84 Y120.201 E.02397
G1 X198.242 Y117.603 E.13443
G3 X197.932 Y117.948 I-1.878 J-1.382 E.017
G1 X200.84 Y120.856 E.1505
G1 X200.84 Y121.511 E.02397
G1 X197.585 Y118.256 E.16845
G3 X197.201 Y118.527 I-1.547 J-1.78 E.01722
G1 X200.84 Y122.166 E.18831
G1 X200.84 Y122.821 E.02397
G1 X196.779 Y118.76 E.21017
G3 X196.313 Y118.949 I-3.148 J-7.074 E.0184
G1 X200.84 Y123.476 E.23426
G1 X200.84 Y124.132 E.02397
G1 X195.791 Y119.082 E.26129
G3 X195.207 Y119.153 I-.649 J-2.887 E.02155
G1 X200.84 Y124.787 E.29149
G1 X200.84 Y125.442 E.02397
G1 X194.29 Y118.891 E.33896
; WIPE_START
G1 X194.997 Y119.598 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I1.175 J-.319 P1  F60000
G1 X192.802 Y111.508 Z.6
G1 Z.2
G1 E.4 F1800
G1 F6300
M204 S500
G1 X192.454 Y111.16 E.01803
G1 X191.799 Y111.16 E.02397
G1 X192.402 Y111.762 E.03119
G2 X192.051 Y112.066 I1.085 J1.607 E.01703
G1 X191.144 Y111.16 E.04692
G1 X190.489 Y111.16 E.02397
G1 X191.743 Y112.414 E.06492
G2 X191.473 Y112.799 I1.788 J1.544 E.01723
G1 X189.834 Y111.16 E.08483
G1 X189.179 Y111.16 E.02397
G1 X191.242 Y113.223 E.10676
G2 X191.053 Y113.689 I2.234 J1.175 E.01844
G1 X189.16 Y111.796 E.09797
G1 X189.16 Y112.451 E.02397
G1 X190.915 Y114.207 E.09085
G2 X190.848 Y114.794 I2.902 J.631 E.02167
G1 X189.16 Y113.106 E.08735
G1 X189.16 Y113.761 E.02397
G1 X191.111 Y115.713 E.10098
; WIPE_START
G1 X190.404 Y115.005 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I.585 J-1.067 P1  F60000
G1 X188.954 Y114.21 Z.6
G1 Z.2
G1 E.4 F1800
G1 F6300
M204 S500
G1 X191.052 Y116.309 E.10858
G2 X193.689 Y118.945 I3.918 J-1.282 E.14155
G1 X200.84 Y126.097 E.37007
G1 X200.84 Y126.752 E.02397
G1 X189.16 Y115.071 E.60442
G1 X189.16 Y115.726 E.02397
G1 X200.84 Y127.407 E.60442
G1 X200.84 Y128.062 E.02397
G1 X189.16 Y116.381 E.60442
G1 X189.16 Y117.036 E.02397
M73 P9 R13
G1 X200.84 Y128.717 E.60442
M73 P10 R13
G1 X200.84 Y129.372 E.02397
G1 X189.16 Y117.691 E.60441
G1 X189.16 Y118.347 E.02397
G1 X200.84 Y130.027 E.60442
G1 X200.84 Y130.682 E.02397
G1 X189.16 Y119.002 E.60442
G1 X189.16 Y119.657 E.02397
G1 X200.84 Y131.337 E.60441
G1 X200.84 Y131.992 E.02397
G1 X188.954 Y120.106 E.61506
; WIPE_START
G1 X189.661 Y120.813 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-.798 J.919 P1  F60000
G1 X204.546 Y133.733 Z.6
G1 Z.2
G1 E.4 F1800
G1 F6300
M204 S500
G1 X203.973 Y133.16 E.02965
G1 X203.318 Y133.16 E.02397
G1 X204.34 Y134.182 E.05291
G1 X204.34 Y134.837 E.02397
G1 X202.663 Y133.16 E.0868
G1 X202.008 Y133.16 E.02397
G1 X204.34 Y135.492 E.1207
G1 X204.34 Y136.147 E.02397
G1 X201.353 Y133.16 E.1546
G1 X200.84 Y133.16 E.01875
G1 X200.84 Y132.647 E.01875
G1 X189.16 Y120.967 E.60442
G1 X189.16 Y121.622 E.02397
G1 X204.34 Y136.802 E.78552
G1 X204.34 Y137.457 E.02397
G1 X189.16 Y122.277 E.78552
G1 X189.16 Y122.932 E.02397
G1 X204.34 Y138.113 E.78552
G1 X204.34 Y138.768 E.02397
G1 X189.16 Y123.587 E.78552
G1 X189.16 Y124.242 E.02397
G1 X204.34 Y139.423 E.78552
G1 X204.34 Y139.998 E.02106
G1 X204.082 Y139.819 E.01152
G1 X189.16 Y124.897 E.77214
G1 X189.16 Y125.552 E.02397
G1 X202.913 Y139.306 E.71169
G2 X202.145 Y139.193 I-.851 J3.108 E.02849
G1 X189.16 Y126.207 E.67193
G1 X189.16 Y126.862 E.02397
G1 X201.517 Y139.22 E.63944
G2 X200.975 Y139.333 I.735 J4.883 E.02027
G1 X189.16 Y127.517 E.61139
G1 X189.16 Y128.172 E.02397
G1 X200.49 Y139.502 E.58627
G2 X200.055 Y139.723 I2.295 J5.048 E.01783
G1 X189.16 Y128.828 E.5638
G1 X189.16 Y129.483 E.02397
G1 X197.716 Y138.039 E.44276
G2 X196.593 Y137.571 I-2.611 J4.681 E.04463
G1 X189.16 Y130.138 E.38464
G1 X189.16 Y130.793 E.02397
G1 X195.765 Y137.398 E.34177
G2 X195.059 Y137.347 I-.614 J3.582 E.02594
M73 P11 R13
G1 X189.16 Y131.448 E.30524
G1 X189.16 Y132.103 E.02397
G1 X194.43 Y137.373 E.2727
G2 X193.862 Y137.461 I.32 J3.953 E.02103
G1 X189.16 Y132.758 E.24334
G1 X189.16 Y133.16 E.0147
G1 X188.906 Y133.16 E.00927
G1 X193.34 Y137.593 E.22942
G2 X192.855 Y137.763 I.894 J3.327 E.01882
G1 X188.251 Y133.16 E.23822
G1 X187.596 Y133.16 E.02397
G1 X192.406 Y137.969 E.24887
G1 X191.991 Y138.209 E.01755
G1 X186.941 Y133.16 E.26128
G1 X186.286 Y133.16 E.02397
G1 X191.604 Y138.477 E.27515
G2 X191.241 Y138.769 I1.277 J1.959 E.01708
G1 X185.66 Y133.188 E.28878
G1 X185.66 Y133.843 E.02397
G1 X190.909 Y139.093 E.27162
G2 X190.603 Y139.442 I2.99 J2.931 E.01699
G1 X185.66 Y134.498 E.25578
G1 X185.66 Y135.153 E.02397
G1 X190.321 Y139.815 E.24119
G1 X190.247 Y139.935 E.00516
G2 X189.26 Y139.409 I-2.047 J2.654 E.04111
G1 X185.66 Y135.809 E.18632
G1 X185.66 Y136.464 E.02397
G1 X188.408 Y139.212 E.14223
G2 X187.739 Y139.198 I-.408 J3.333 E.02455
G1 X185.66 Y137.119 E.10758
G1 X185.66 Y137.774 E.02397
G1 X187.168 Y139.282 E.07806
G2 X186.665 Y139.434 I1.052 J4.411 E.01925
G1 X185.66 Y138.429 E.052
G1 X185.66 Y139.084 E.02397
G1 X186.213 Y139.637 E.02862
G2 X185.812 Y139.891 I.871 J1.814 E.01741
G1 X185.454 Y139.533 E.01854
; OBJECT_ID: 8
; WIPE_START
G1 X185.812 Y139.891 E-.19251
G1 X186.213 Y139.637 E-.18035
G1 X186.2 Y139.624 E-.00715
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 12
M625
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S6000
G17
G3 Z.6 I.581 J-1.069 P1  F60000
G1 X141.52 Y115.329 Z.6
G1 Z.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.5
G1 F3000
M204 S500
G1 X141.52 Y174.529 E2.13748
G1 X140.48 Y174.529 E.03754
G1 X140.48 Y115.329 E2.13748
G1 X121.761 Y115.329 E.67587
G1 X121.761 Y113.871 E.05263
G1 X157.229 Y113.871 E1.2806
G1 X157.229 Y115.329 E.05263
G1 X155.52 Y115.329 E.0617
G1 X155.52 Y174.529 E2.13748
G1 X154.48 Y174.529 E.03754
G1 X154.48 Y115.329 E2.13748
M73 P12 R13
G1 X141.58 Y115.329 E.46578
M204 S6000
G1 X141.977 Y115.786 F60000
G1 F3000
M204 S500
G1 X141.977 Y174.986 E2.13748
G1 X140.023 Y174.986 E.07054
G1 X140.023 Y115.786 E2.13748
G1 X121.304 Y115.786 E.67587
G1 X121.304 Y113.414 E.08563
G1 X157.686 Y113.414 E1.3136
G1 X157.686 Y115.786 E.08563
G1 X155.977 Y115.786 E.0617
G1 X155.977 Y174.986 E2.13748
G1 X154.023 Y174.986 E.07054
G1 X154.023 Y115.786 E2.13748
G1 X142.037 Y115.786 E.43278
M204 S6000
G1 X142.434 Y116.243 F60000
G1 F3000
M204 S500
M73 P13 R13
G1 X142.434 Y175.157 E2.12715
G1 X143.035 Y175.157 E.02171
G1 X143.035 Y175.443 E.01032
G1 X141.528 Y175.443 E.05442
G1 X141.528 Y185.742 E.37185
G1 X141.224 Y186.042 E.01541
G1 X141.224 Y186.897 E.0309
G1 X141 Y187.084 E.01053
G1 X140.776 Y186.897 E.01053
G1 X140.776 Y186.042 E.0309
G1 X140.472 Y185.742 E.01541
G1 X140.472 Y175.443 E.37185
G1 X138.965 Y175.443 E.05442
G1 X138.965 Y175.157 E.01032
G1 X139.566 Y175.157 E.02171
G1 X139.566 Y116.243 E2.12715
G1 X120.847 Y116.243 E.67587
G1 X120.847 Y112.957 E.11864
G1 X158.143 Y112.957 E1.34661
G1 X158.143 Y116.243 E.11864
G1 X156.434 Y116.243 E.0617
G1 X156.434 Y175.157 E2.12715
G1 X157.035 Y175.157 E.02171
G1 X157.035 Y175.443 E.01032
G1 X155.528 Y175.443 E.05442
G1 X155.528 Y185.742 E.37185
G1 X155.224 Y186.042 E.01541
G1 X155.224 Y186.397 E.01284
G1 X155 Y186.584 E.01053
G1 X154.776 Y186.397 E.01053
G1 X154.776 Y186.042 E.01285
G1 X154.472 Y185.742 E.01541
G1 X154.472 Y175.443 E.37185
G1 X152.965 Y175.443 E.05442
G1 X152.965 Y175.157 E.01032
G1 X153.566 Y175.157 E.02171
G1 X153.566 Y116.243 E2.12715
G1 X142.494 Y116.243 E.39977
M204 S6000
G1 X142.891 Y116.7 F60000
; FEATURE: Outer wall
G1 F3000
M204 S500
G1 X142.891 Y174.7 E2.09415
G1 X143.492 Y174.7 E.02171
G1 X143.492 Y175.9 E.04333
M73 P14 R13
G1 X141.985 Y175.9 E.05442
G1 X141.985 Y185.933 E.36225
G1 X141.682 Y186.233 E.01541
G1 X141.682 Y187.112 E.03175
G3 X141.209 Y187.5 I-6.432 J-7.354 E.02208
G1 X140.791 Y187.5 E.01509
G3 X140.318 Y187.112 I5.943 J-7.722 E.02208
G1 X140.318 Y186.233 E.03175
G1 X140.015 Y185.933 E.01541
G1 X140.015 Y175.9 E.36225
G1 X138.508 Y175.9 E.05442
G1 X138.508 Y174.7 E.04333
G1 X139.109 Y174.7 E.02171
G1 X139.109 Y116.7 E2.09415
G1 X120.39 Y116.7 E.67587
G1 X120.39 Y112.5 E.15165
G1 X158.6 Y112.5 E1.37961
G1 X158.6 Y116.7 E.15165
G1 X156.891 Y116.7 E.0617
G1 X156.891 Y174.7 E2.09415
G1 X157.492 Y174.7 E.02171
G1 X157.492 Y175.9 E.04333
G1 X155.985 Y175.9 E.05442
G1 X155.985 Y185.933 E.36225
G1 X155.682 Y186.233 E.01541
G1 X155.682 Y186.612 E.0137
G3 X155.209 Y187 I-6.432 J-7.354 E.02208
G1 X154.791 Y187 E.0151
G3 X154.318 Y186.612 I6.318 J-8.172 E.02207
G1 X154.318 Y186.233 E.0137
G1 X154.015 Y185.933 E.01541
G1 X154.015 Y175.9 E.36225
G1 X152.508 Y175.9 E.05442
G1 X152.508 Y174.7 E.04333
G1 X153.109 Y174.7 E.02171
G1 X153.109 Y116.7 E2.09415
G1 X142.951 Y116.7 E.36676
; WIPE_START
G1 X142.95 Y117.7 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I.974 J-.73 P1  F60000
G1 X141 Y115.1 Z.6
G1 Z.2
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.62546
G1 F3000
M204 S500
G1 X141 Y174.3 E2.72417
M204 S6000
G1 X141 Y175.215 F60000
; LINE_WIDTH: 0.64212
G1 F3000
M204 S500
M73 P15 R13
G1 X141 Y185.942 E.50776
; WIPE_START
G1 X141 Y184.942 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-.087 J1.214 P1  F60000
G1 X155 Y185.942 Z.6
G1 Z.2
G1 E.4 F1800
G1 F3000
M204 S500
G1 X155 Y175.215 E.50776
M204 S6000
G1 X155 Y174.3 F60000
; LINE_WIDTH: 0.62546
G1 F3000
M204 S500
G1 X155 Y115.1 E2.72417
; WIPE_START
G1 X155 Y116.1 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I.584 J1.067 P1  F60000
G1 X157.046 Y114.98 Z.6
G1 Z.2
G1 E.4 F1800
; FEATURE: Bottom surface
; LINE_WIDTH: 0.50109
G1 F6300
M204 S500
G1 X156.325 Y114.26 E.03688
G1 X155.678 Y114.26 E.02345
G1 X156.358 Y114.94 E.03484
G1 X155.71 Y114.94 E.02345
G1 X155.03 Y114.26 E.03484
G1 X154.382 Y114.26 E.02345
G1 X154.834 Y114.712 E.02315
G1 X154.299 Y114.712 E.01937
G1 X154.299 Y114.825 E.00408
G1 X153.734 Y114.26 E.02892
G1 X153.086 Y114.26 E.02345
G1 X153.766 Y114.94 E.03484
G1 X153.119 Y114.94 E.02345
G1 X152.438 Y114.26 E.03484
G1 X151.79 Y114.26 E.02345
G1 X152.471 Y114.94 E.03484
G1 X151.823 Y114.94 E.02345
G1 X151.142 Y114.26 E.03484
G1 X150.494 Y114.26 E.02345
G1 X151.175 Y114.94 E.03484
G1 X150.527 Y114.94 E.02345
G1 X149.846 Y114.26 E.03484
G1 X149.198 Y114.26 E.02345
G1 X149.879 Y114.94 E.03484
G1 X149.231 Y114.94 E.02345
G1 X148.55 Y114.26 E.03484
G1 X147.902 Y114.26 E.02345
G1 X148.583 Y114.94 E.03484
G1 X147.935 Y114.94 E.02345
G1 X147.254 Y114.26 E.03484
G1 X146.606 Y114.26 E.02345
G1 X147.287 Y114.94 E.03484
G1 X146.639 Y114.94 E.02345
G1 X145.958 Y114.26 E.03484
G1 X145.31 Y114.26 E.02345
G1 X145.991 Y114.94 E.03484
G1 X145.343 Y114.94 E.02345
G1 X144.662 Y114.26 E.03484
G1 X144.014 Y114.26 E.02345
G1 X144.695 Y114.94 E.03484
G1 X144.047 Y114.94 E.02345
G1 X143.366 Y114.26 E.03484
G1 X142.719 Y114.26 E.02345
G1 X143.399 Y114.94 E.03484
G1 X142.751 Y114.94 E.02345
G1 X142.071 Y114.26 E.03484
G1 X141.423 Y114.26 E.02345
G1 X142.103 Y114.94 E.03484
G1 X141.701 Y114.94 E.01455
G1 X141.701 Y114.712 E.00827
G1 X141.227 Y114.712 E.01716
G1 X140.775 Y114.26 E.02315
G1 X140.127 Y114.26 E.02345
G1 X140.579 Y114.712 E.02315
G1 X140.299 Y114.712 E.01014
G1 X140.299 Y114.94 E.00827
G1 X140.16 Y114.94 E.00504
G1 X139.479 Y114.26 E.03484
G1 X138.831 Y114.26 E.02345
G1 X139.512 Y114.94 E.03484
G1 X138.864 Y114.94 E.02345
G1 X138.183 Y114.26 E.03484
G1 X137.535 Y114.26 E.02345
G1 X138.216 Y114.94 E.03484
G1 X137.568 Y114.94 E.02345
G1 X136.887 Y114.26 E.03484
G1 X136.239 Y114.26 E.02345
G1 X136.92 Y114.94 E.03484
G1 X136.272 Y114.94 E.02345
G1 X135.591 Y114.26 E.03484
G1 X134.943 Y114.26 E.02345
G1 X135.624 Y114.94 E.03484
G1 X134.976 Y114.94 E.02345
G1 X134.295 Y114.26 E.03484
G1 X133.647 Y114.26 E.02345
G1 X134.328 Y114.94 E.03484
G1 X133.68 Y114.94 E.02345
G1 X132.999 Y114.26 E.03484
G1 X132.351 Y114.26 E.02345
G1 X133.032 Y114.94 E.03484
G1 X132.384 Y114.94 E.02345
G1 X131.703 Y114.26 E.03484
G1 X131.055 Y114.26 E.02345
G1 X131.736 Y114.94 E.03484
G1 X131.088 Y114.94 E.02345
G1 X130.407 Y114.26 E.03484
G1 X129.759 Y114.26 E.02345
G1 X130.44 Y114.94 E.03484
G1 X129.792 Y114.94 E.02345
G1 X129.112 Y114.26 E.03484
G1 X128.464 Y114.26 E.02345
G1 X129.144 Y114.94 E.03484
G1 X128.496 Y114.94 E.02345
G1 X127.816 Y114.26 E.03484
G1 X127.168 Y114.26 E.02345
G1 X127.848 Y114.94 E.03484
G1 X127.201 Y114.94 E.02345
G1 X126.52 Y114.26 E.03484
G1 X125.872 Y114.26 E.02345
G1 X126.553 Y114.94 E.03484
G1 X125.905 Y114.94 E.02345
G1 X125.224 Y114.26 E.03484
G1 X124.576 Y114.26 E.02345
G1 X125.257 Y114.94 E.03484
G1 X124.609 Y114.94 E.02345
G1 X123.928 Y114.26 E.03484
G1 X123.28 Y114.26 E.02345
G1 X123.961 Y114.94 E.03484
G1 X123.313 Y114.94 E.02345
G1 X122.632 Y114.26 E.03484
G1 X122.15 Y114.26 E.01746
G1 X122.15 Y114.425 E.00599
G1 X122.871 Y115.146 E.0369
; WIPE_START
G1 X122.163 Y114.439 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I-.136 J-1.209 P1  F60000
G1 X114.239 Y115.329 Z.6
G1 Z.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.5
G1 F3000
M204 S500
G1 X112.771 Y115.329 E.05299
G1 X112.771 Y113.871 E.05263
G1 X114.239 Y113.871 E.05299
G1 X114.239 Y115.269 E.05046
M204 S6000
G1 X114.696 Y115.786 F60000
M73 P16 R13
G1 F3000
M204 S500
G1 X112.314 Y115.786 E.086
G1 X112.314 Y113.414 E.08563
G1 X114.696 Y113.414 E.086
G1 X114.696 Y115.726 E.08347
M204 S6000
G1 X115.153 Y116.243 F60000
G1 F3000
M204 S500
G1 X111.857 Y116.243 E.119
G1 X111.857 Y112.957 E.11864
G1 X115.153 Y112.957 E.119
G1 X115.153 Y116.183 E.11647
M204 S6000
G1 X115.61 Y116.7 F60000
; FEATURE: Outer wall
G1 F3000
M204 S500
G1 X111.4 Y116.7 E.15201
G1 X111.4 Y112.5 E.15165
G1 X115.61 Y112.5 E.15201
G1 X115.61 Y116.64 E.14948
; WIPE_START
G1 X114.61 Y116.654 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S6000
G17
G3 Z.6 I1.027 J-.652 P1  F60000
G1 X112.959 Y114.054 Z.6
G1 Z.2
G1 E.4 F1800
; FEATURE: Bottom surface
; LINE_WIDTH: 0.58166
G1 F6300
M204 S500
G1 X114.051 Y115.146 E.06573
; CHANGE_LAYER
; Z_HEIGHT: 0.4
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F6300
G1 X113.344 Y114.439 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 2/27
; update layer progress
M73 L2
M991 S0 P1 ;notify layer change
; open powerlost recovery
M1003 S1
M104 S250 ; set nozzle temperature
; OBJECT_ID: 16
; start printing object, unique label id: 16
M624 BAAAAAAAAAA=
M204 S10000
G17
G3 Z.6 I-.751 J.958 P1  F60000
G1 X194.96 Y178.414 Z.6
G1 Z.4
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X194.745 Y178.404 E.00694
G3 X194.575 Y171.609 I.255 J-3.406 E.32317
G1 X194.915 Y171.583 E.01097
G3 X195.085 Y178.413 I.085 J3.415 E.34507
G1 X195.02 Y178.413 E.00208
M204 S10000
G1 X194.97 Y178.007 F60000
G1 F13265.217
M204 S8000
G1 X194.775 Y177.998 E.00628
G3 X194.625 Y172.013 I.225 J-3 E.28463
G1 X194.925 Y171.991 E.00966
G3 X195.075 Y178.006 I.075 J3.008 E.30392
G1 X195.03 Y178.006 E.00143
M204 S10000
G1 X194.981 Y177.6 F60000
G1 F13265.217
M204 S8000
G1 X194.806 Y177.592 E.00563
G3 X194.676 Y172.417 I.194 J-2.594 E.24609
G1 X194.935 Y172.398 E.00835
G3 X195.065 Y177.599 I.065 J2.6 E.26278
G1 X195.041 Y177.599 E.00078
M204 S250
G1 X194.988 Y177.2 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X194.835 Y177.201 E.00457
G3 X194.725 Y172.807 I.165 J-2.203 E.19358
G1 X194.945 Y172.79 E.00657
G3 X195.275 Y177.19 I.055 J2.208 E.20013
G1 X195.048 Y177.198 E.00674
; WIPE_START
M204 S8000
G1 X194.835 Y177.201 E-.08109
G1 X194.401 Y177.128 E-.16721
G1 X194.079 Y177.001 E-.1317
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I-1.059 J.599 P1  F60000
G1 X202.79 Y192.416 Z.8
G1 Z.4
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X205.084 Y192.416 E.07376
G1 X205.084 Y201.923 E.3057
G1 X204.888 Y201.963 E.00642
G2 X199.556 Y201.146 I-2.888 J1.045 E.21173
G2 X190.449 Y201.135 I-4.556 J1.859 E.37407
G2 X185.111 Y201.961 I-2.44 J1.895 E.21136
G1 X184.916 Y201.921 E.00641
G1 X184.916 Y192.416 E.30562
G1 X188.416 Y192.416 E.11255
G1 X188.416 Y170.416 E.70744
G1 X201.584 Y170.416 E.42342
G1 X201.584 Y192.416 E.70744
G1 X202.73 Y192.416 E.03686
M204 S10000
G1 X202.79 Y192.009 F60000
M73 P16 R12
G1 F13265.217
M204 S8000
G1 X205.491 Y192.009 E.08685
G1 X205.491 Y209.991 E.57823
G1 X204.909 Y209.991 E.01871
G1 X204.909 Y208.991 E.03216
G1 X204.659 Y208.991 E.00804
G1 X204.659 Y202.975 E.19344
G2 X199.558 Y201.953 I-2.658 J.024 E.23315
G1 X199.385 Y201.941 E.00555
G2 X190.615 Y201.941 I-4.385 J1.063 E.38683
G1 X190.442 Y201.952 E.00557
G2 X185.341 Y202.975 I-2.441 J1.059 E.23258
G1 X185.341 Y208.991 E.19344
G1 X185.091 Y208.991 E.00804
G1 X185.091 Y209.991 E.03216
G1 X184.509 Y209.991 E.01871
G1 X184.509 Y192.009 E.57823
G1 X188.009 Y192.009 E.11255
G1 X188.009 Y170.009 E.70744
G1 X201.991 Y170.009 E.4496
G1 X201.991 Y192.009 E.70744
G1 X202.73 Y192.009 E.02377
M204 S10000
G1 X202.79 Y191.602 F60000
G1 F13265.217
M204 S8000
G1 X205.898 Y191.602 E.09994
G1 X205.898 Y210.398 E.60441
G1 X204.502 Y210.398 E.04489
G1 X204.502 Y209.398 E.03216
G1 X204.252 Y209.398 E.00804
G1 X204.252 Y202.985 E.20621
G2 X199.748 Y202.985 I-2.252 J.021 E.22618
G1 X199.748 Y209.398 E.20621
G1 X199.498 Y209.398 E.00804
G1 X199.498 Y210.398 E.03216
G1 X199.102 Y210.398 E.01273
G1 X199.102 Y202.992 E.23814
G2 X190.898 Y202.988 I-4.102 J.009 E.4137
G1 X190.898 Y210.398 E.23827
G1 X190.502 Y210.398 E.01273
G1 X190.502 Y209.398 E.03216
G1 X190.252 Y209.398 E.00804
G1 X190.252 Y202.985 E.20621
G2 X185.748 Y202.985 I-2.252 J.021 E.22618
G1 X185.748 Y209.398 E.20621
G1 X185.498 Y209.398 E.00804
G1 X185.498 Y210.398 E.03216
G1 X184.102 Y210.398 E.04489
G1 X184.102 Y191.602 E.60441
G1 X187.602 Y191.602 E.11255
G1 X187.602 Y169.602 E.70744
G1 X202.398 Y169.602 E.47578
G1 X202.398 Y191.602 E.70744
G1 X202.73 Y191.602 E.01068
M204 S250
G1 X202.79 Y191.21 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X206.29 Y191.21 E.10425
G1 X206.29 Y210.79 E.58322
; object ids of layer 2 start: 8,12,16
M624 BwAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer2 end: 8,12,16
M625
G1 X204.11 Y210.79 E.06494
G1 X204.11 Y209.79 E.02979
G1 X203.86 Y209.79 E.00745
G1 X203.86 Y202.995 E.2024
G2 X200.14 Y202.995 I-1.86 J.01 E.17345
G1 X200.14 Y209.79 E.2024
G1 X199.89 Y209.79 E.00745
G1 X199.89 Y210.79 E.02979
G1 X198.71 Y210.79 E.03515
G1 X198.71 Y202.997 E.23212
G2 X191.29 Y202.996 I-3.71 J.004 E.3469
G1 X191.29 Y210.79 E.23216
G1 X190.11 Y210.79 E.03515
G1 X190.11 Y209.79 E.02979
G1 X189.86 Y209.79 E.00745
G1 X189.86 Y202.995 E.2024
G2 X186.14 Y202.995 I-1.86 J.01 E.17345
G1 X186.14 Y209.79 E.2024
G1 X185.89 Y209.79 E.00745
G1 X185.89 Y210.79 E.02979
G1 X183.71 Y210.79 E.06494
G1 X183.71 Y191.21 E.58322
G1 X187.21 Y191.21 E.10425
G1 X187.21 Y169.21 E.65531
G1 X202.79 Y169.21 E.46408
G1 X202.79 Y191.15 E.65352
; WIPE_START
M204 S8000
G1 X203.79 Y191.167 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I-1.215 J.065 P1  F60000
G1 X204.301 Y200.735 Z.8
G1 Z.4
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42264
G1 F14221.004
M204 S8000
G1 X204.751 Y200.285 E.01906
G1 X204.751 Y199.748 E.01611
G1 X204.135 Y200.364 E.02611
G2 X203.827 Y200.135 I-1.075 J1.129 E.01154
G1 X204.751 Y199.211 E.03919
G1 X204.751 Y198.674 E.01611
G1 X203.478 Y199.947 E.05398
G2 X203.102 Y199.786 I-.824 J1.406 E.0123
G1 X204.751 Y198.137 E.06994
G1 X204.751 Y197.6 E.01611
G1 X202.68 Y199.671 E.08782
G2 X202.202 Y199.612 I-.463 J1.813 E.01451
G1 X204.751 Y197.063 E.10812
G1 X204.751 Y196.526 E.01611
G1 X201.658 Y199.619 E.13118
G2 X200.98 Y199.76 I.219 J2.754 E.02082
G1 X204.751 Y195.989 E.15994
G1 X204.751 Y195.452 E.01611
G1 X199.641 Y200.551 E.21652
G2 X199.449 Y200.217 I-3.803 J1.959 E.01155
G1 X204.751 Y194.915 E.22489
G1 X204.751 Y194.378 E.01611
G1 X199.231 Y199.898 E.23412
G2 X198.995 Y199.597 I-3.64 J2.611 E.01148
G1 X204.751 Y193.841 E.24413
G1 X204.751 Y193.304 E.01611
G1 X198.737 Y199.318 E.25509
G2 X198.459 Y199.059 I-1.434 J1.259 E.01142
G1 X204.751 Y192.767 E.26688
G1 X204.751 Y192.749 E.00054
G1 X204.231 Y192.749 E.01557
G1 X198.166 Y198.814 E.25727
G2 X197.847 Y198.597 I-1.616 J2.025 E.0116
G1 X203.694 Y192.749 E.24803
G1 X203.157 Y192.749 E.01611
G1 X197.514 Y198.393 E.23939
G2 X197.157 Y198.213 I-1.985 J3.504 E.012
G1 X202.62 Y192.749 E.23177
G1 X202.083 Y192.749 E.01611
G1 X196.771 Y198.062 E.22535
G2 X196.36 Y197.935 I-.838 J1.989 E.01291
G1 X201.546 Y192.749 E.21998
G1 X201.251 Y192.749 E.00887
G1 X201.251 Y192.508 E.00723
M73 P17 R12
G1 X195.926 Y197.833 E.22586
G2 X195.441 Y197.781 I-.504 J2.435 E.01467
G1 X201.251 Y191.971 E.24645
G1 X201.251 Y191.434 E.01611
G1 X194.933 Y197.752 E.26798
G2 X194.358 Y197.79 I-.034 J3.857 E.0173
G1 X201.251 Y190.897 E.29237
G1 X201.251 Y190.36 E.01611
G1 X193.694 Y197.917 E.32054
G2 X192.872 Y198.202 I1.319 J5.13 E.02614
G1 X201.251 Y189.823 E.35542
G1 X201.251 Y189.286 E.01611
G1 X190.156 Y200.381 E.47064
G2 X189.85 Y200.15 I-1.083 J1.117 E.01153
G1 X201.251 Y188.749 E.48362
G1 X201.251 Y188.212 E.01611
G1 X189.503 Y199.959 E.49831
G2 X189.13 Y199.796 I-.834 J1.394 E.01226
G1 X201.251 Y187.675 E.51414
G1 X201.251 Y187.138 E.01611
G1 X188.711 Y199.678 E.53191
G2 X188.242 Y199.61 I-.801 J3.871 E.01422
G1 X201.251 Y186.601 E.55181
G1 X201.251 Y186.064 E.01611
G1 X187.701 Y199.613 E.57475
G2 X187.031 Y199.747 I.193 J2.721 E.02056
G1 X201.251 Y185.527 E.60319
G1 X201.251 Y184.99 E.01611
G1 X185.94 Y200.3 E.64945
G2 X185.377 Y200.846 I1.818 J2.441 E.02358
G1 X185.249 Y200.743 E.00492
G1 X185.249 Y200.454 E.00865
G1 X201.251 Y184.453 E.67876
G1 X201.251 Y183.916 E.01611
G1 X185.249 Y199.917 E.67876
G1 X185.249 Y199.38 E.01611
G1 X201.251 Y183.379 E.67876
G1 X201.251 Y182.842 E.01611
G1 X185.249 Y198.843 E.67876
G1 X185.249 Y198.306 E.01611
G1 X201.251 Y182.305 E.67876
G1 X201.251 Y181.768 E.01611
G1 X185.249 Y197.769 E.67876
G1 X185.249 Y197.232 E.01611
G1 X201.251 Y181.231 E.67876
G1 X201.251 Y180.694 E.01611
G1 X185.249 Y196.695 E.67876
G1 X185.249 Y196.158 E.01611
G1 X201.251 Y180.157 E.67876
G1 X201.251 Y179.62 E.01611
G1 X188.749 Y192.121 E.53029
G1 X188.749 Y191.584 E.01611
G1 X201.251 Y179.083 E.53029
G1 X201.251 Y178.546 E.01611
G1 X188.749 Y191.047 E.53029
G1 X188.749 Y190.51 E.01611
G1 X201.251 Y178.009 E.53029
G1 X201.251 Y177.472 E.01611
G1 X188.749 Y189.973 E.53029
G1 X188.749 Y189.436 E.01611
G1 X201.251 Y176.935 E.53029
G1 X201.251 Y176.398 E.01611
G1 X188.749 Y188.899 E.53029
G1 X188.749 Y188.362 E.01611
G1 X201.251 Y175.861 E.53029
G1 X201.251 Y175.324 E.01611
G1 X188.749 Y187.825 E.53029
G1 X188.749 Y187.288 E.01611
G1 X201.251 Y174.787 E.53029
G1 X201.251 Y174.25 E.01611
G1 X188.749 Y186.751 E.53029
G1 X188.749 Y186.214 E.01611
G1 X196.543 Y178.42 E.33061
G3 X195.755 Y178.672 I-1.693 J-3.936 E.02485
G1 X188.749 Y185.677 E.29717
G1 X188.749 Y185.14 E.01611
G1 X195.143 Y178.747 E.2712
G3 X194.624 Y178.729 I-.099 J-4.733 E.01559
G1 X188.749 Y184.603 E.24917
G1 X188.749 Y184.066 E.01611
G1 X194.163 Y178.652 E.22965
G3 X193.747 Y178.532 I.395 J-2.143 E.01303
G1 X188.749 Y183.529 E.21199
G1 X188.749 Y182.992 E.01611
G1 X193.367 Y178.374 E.19589
G3 X193.022 Y178.183 I.788 J-1.828 E.01187
G1 X188.749 Y182.455 E.18124
G1 X188.749 Y181.918 E.01611
G1 X192.704 Y177.964 E.16774
G3 X192.415 Y177.716 I1.097 J-1.57 E.01144
G1 X188.749 Y181.381 E.15548
G1 X188.749 Y180.844 E.01611
G1 X192.153 Y177.441 E.14438
G3 X191.919 Y177.138 I1.395 J-1.321 E.0115
G1 X188.749 Y180.307 E.13444
G1 X188.749 Y179.77 E.01611
G1 X191.714 Y176.805 E.12576
G3 X191.538 Y176.444 I7.918 J-4.081 E.01205
G1 X188.749 Y179.233 E.1183
G1 X188.749 Y178.696 E.01611
G1 X191.4 Y176.046 E.11242
G3 X191.302 Y175.606 I2.149 J-.708 E.01352
G1 X188.749 Y178.159 E.10828
G1 X188.749 Y177.622 E.01611
G1 X191.254 Y175.117 E.10625
G3 X191.281 Y174.554 I3.621 J-.111 E.01695
G1 X188.749 Y177.085 E.10739
G1 X188.749 Y176.548 E.01611
G1 X191.716 Y173.582 E.12582
; WIPE_START
G1 X191.009 Y174.289 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I1.111 J-.497 P1  F60000
G1 X189.348 Y170.58 Z.8
G1 Z.4
G1 E.4 F1800
G1 F14221.004
M204 S8000
G1 X188.749 Y171.178 E.02538
G1 X188.749 Y171.715 E.01611
G1 X189.715 Y170.749 E.04096
G1 X190.252 Y170.749 E.01611
G1 X188.749 Y172.252 E.06374
G1 X188.749 Y172.789 E.01611
G1 X190.789 Y170.749 E.08652
G1 X191.326 Y170.749 E.01611
G1 X188.749 Y173.326 E.1093
G1 X188.749 Y173.863 E.01611
G1 X191.863 Y170.749 E.13208
G1 X192.4 Y170.749 E.01611
G1 X188.749 Y174.4 E.15486
G1 X188.749 Y174.937 E.01611
G1 X192.937 Y170.749 E.17764
G1 X193.474 Y170.749 E.01611
G1 X188.749 Y175.474 E.20042
G1 X188.749 Y176.011 E.01611
G1 X194.011 Y170.749 E.2232
G1 X194.548 Y170.749 E.01611
G1 X193.873 Y171.425 E.02864
G3 X194.559 Y171.276 I1.35 J4.562 E.02108
G1 X195.085 Y170.749 E.02232
G1 X195.622 Y170.749 E.01611
G1 X195.117 Y171.255 E.02143
G3 X195.609 Y171.3 I.02 J2.48 E.01484
G1 X196.159 Y170.749 E.02335
G1 X196.696 Y170.749 E.01611
G1 X196.047 Y171.399 E.02755
G3 X196.442 Y171.54 I-.506 J2.044 E.01263
G1 X197.233 Y170.749 E.03354
G1 X197.77 Y170.749 E.01611
G1 X196.803 Y171.716 E.04102
G3 X197.136 Y171.921 I-.852 J1.761 E.01173
G1 X198.307 Y170.749 E.04968
G1 X198.844 Y170.749 E.01611
G1 X197.439 Y172.155 E.05961
G3 X197.714 Y172.416 I-1.17 J1.508 E.01141
G1 X199.381 Y170.749 E.07071
G1 X199.918 Y170.749 E.01611
G1 X197.962 Y172.705 E.08296
G3 X198.183 Y173.022 I-1.472 J1.258 E.01159
G1 X200.455 Y170.749 E.0964
G1 X200.992 Y170.749 E.01611
G1 X198.373 Y173.368 E.1111
G3 X198.531 Y173.747 I-1.811 J.979 E.01233
G1 X201.251 Y171.028 E.11534
G1 X201.251 Y171.565 E.01611
G1 X198.653 Y174.162 E.11018
G3 X198.732 Y174.621 I-2.253 J.624 E.01397
G1 X201.251 Y172.102 E.10683
G1 X201.251 Y172.639 E.01611
G1 X198.742 Y175.147 E.1064
G3 X198.665 Y175.762 I-2.461 J.002 E.01863
G1 X201.251 Y173.176 E.10969
G1 X201.251 Y173.713 E.01611
G1 X197.971 Y176.992 E.13911
; WIPE_START
G1 X198.678 Y176.285 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I-.946 J-.765 P1  F60000
G1 X185.08 Y193.106 Z.8
G1 Z.4
G1 E.4 F1800
G1 F14221.004
M204 S8000
G1 X185.436 Y192.749 E.01512
G1 X185.973 Y192.749 E.01611
G1 X185.249 Y193.473 E.0307
G1 X185.249 Y194.01 E.01611
G1 X186.51 Y192.749 E.05348
G1 X187.047 Y192.749 E.01611
G1 X185.249 Y194.547 E.07626
G1 X185.249 Y195.084 E.01611
G1 X187.584 Y192.749 E.09904
G1 X188.121 Y192.749 E.01611
G1 X185.08 Y195.791 E.12902
; WIPE_START
G1 X185.787 Y195.084 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I-1.212 J-.105 P1  F60000
G1 X185.258 Y201.178 Z.8
G1 Z.4
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.107986
G1 F15000
M204 S8000
G1 X185.177 Y201.277 E.00066
G2 X185.14 Y201.377 I.106 J.096 E.00056
M204 S10000
G1 X185.247 Y202.196 F60000
; LINE_WIDTH: 0.510273
G1 F11554.448
M204 S8000
G1 X184.954 Y202.396 E.01309
G2 X184.931 Y202.704 I6.112 J.602 E.01139
; LINE_WIDTH: 0.46788
G1 F12707.104
G1 X184.925 Y208.575 E.19709
; LINE_WIDTH: 0.448765
G1 F13305.572
G1 X184.906 Y208.594 E.00085
; LINE_WIDTH: 0.411095
G1 F14666.937
G1 X184.887 Y208.613 E.00077
; LINE_WIDTH: 0.370428
G1 F15000
G1 X184.866 Y208.656 E.00126
; LINE_WIDTH: 0.326763
G1 X184.844 Y208.7 E.00109
; LINE_WIDTH: 0.283098
G1 X184.822 Y208.744 E.00093
; LINE_WIDTH: 0.218607
G1 X184.8 Y208.787 E.00068
G1 X184.8 Y209.787 E.01388
; WIPE_START
G1 X184.8 Y208.787 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I-.086 J1.214 P1  F60000
G1 X190.575 Y209.194 Z.8
G1 Z.4
G1 E.4 F1800
; LINE_WIDTH: 0.282093
G1 F15000
M204 S8000
G1 X190.574 Y202.749 E.12177
; LINE_WIDTH: 0.321263
G1 X190.566 Y202.56 E.00416
; LINE_WIDTH: 0.364923
G1 X190.561 Y202.407 E.00391
; LINE_WIDTH: 0.404148
G1 F14949.002
G1 X190.556 Y202.336 E.002
; LINE_WIDTH: 0.407551
G1 F14809.507
G1 X190.776 Y202.135 E.00857
; WIPE_START
G1 X190.556 Y202.336 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I-.744 J.963 P1  F60000
G1 X199.425 Y209.194 Z.8
G1 Z.4
G1 E.4 F1800
; LINE_WIDTH: 0.28196
G1 F15000
M204 S8000
G2 X199.425 Y202.987 I-462.48 J-3.102 E.11722
G1 X199.427 Y202.782 E.00386
; LINE_WIDTH: 0.317686
G1 X199.434 Y202.56 E.00482
; LINE_WIDTH: 0.365154
G1 X199.44 Y202.405 E.00396
; LINE_WIDTH: 0.404749
G1 F14924.177
G1 X199.444 Y202.337 E.00195
; LINE_WIDTH: 0.407053
G1 F14829.757
G1 X199.224 Y202.135 E.00859
; WIPE_START
G1 X199.444 Y202.337 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I.25 J1.191 P1  F60000
G1 X204.77 Y201.217 Z.8
G1 Z.4
G1 E.4 F1800
; LINE_WIDTH: 0.105325
G1 F15000
M204 S8000
G3 X204.86 Y201.377 I-.176 J.205 E.00092
M204 S10000
G1 X204.753 Y202.198 F60000
; LINE_WIDTH: 0.512729
G1 F11494.036
M204 S8000
G1 X205.045 Y202.386 E.01289
G1 X205.067 Y202.682 E.01103
; LINE_WIDTH: 0.474802
G1 F12503.44
G3 X205.075 Y202.96 I-5.568 J.288 E.00947
; LINE_WIDTH: 0.467502
G1 F12718.408
G1 X205.075 Y208.575 E.18834
G1 X205.094 Y208.594 E.00089
; LINE_WIDTH: 0.411095
G1 F14666.937
G1 X205.113 Y208.613 E.00077
; LINE_WIDTH: 0.370425
G1 F15000
G1 X205.135 Y208.656 E.00126
; LINE_WIDTH: 0.326755
G1 X205.156 Y208.7 E.00109
; LINE_WIDTH: 0.283085
G1 X205.178 Y208.744 E.00093
; LINE_WIDTH: 0.239415
G1 X205.2 Y208.787 E.00076
; LINE_WIDTH: 0.21759
G1 X205.2 Y209.787 E.0138
; OBJECT_ID: 12
; WIPE_START
G1 X205.2 Y208.787 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 16
M625
; start printing object, unique label id: 12
M624 AgAAAAAAAAA=
M204 S10000
G17
G3 Z.8 I1.213 J-.103 P1  F60000
G1 X197.446 Y117.383 Z.8
G1 Z.4
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X197.26 Y117.561 E.00827
G3 X194.575 Y111.609 I-2.26 J-2.562 E.41085
G1 X194.915 Y111.583 E.01096
G3 X197.504 Y117.323 I.085 J3.415 E.25753
G1 X197.488 Y117.34 E.00074
M204 S10000
G1 X197.162 Y117.092 F60000
G1 F13265.217
M204 S8000
G1 X196.991 Y117.256 E.00762
G3 X194.626 Y112.013 I-1.991 J-2.257 E.36187
G1 X194.925 Y111.991 E.00966
G3 X197.205 Y117.046 I.075 J3.008 E.22682
G1 X197.203 Y117.048 E.00009
M204 S10000
G1 X196.877 Y116.8 F60000
G1 F13265.217
M204 S8000
G1 X196.721 Y116.95 E.00697
G3 X194.676 Y112.417 I-1.721 J-1.951 E.31291
G1 X194.935 Y112.398 E.00835
G3 X196.919 Y116.757 I.065 J2.601 E.19556
M204 S250
G1 X196.604 Y116.517 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X196.284 Y116.786 E.01245
G3 X194.725 Y112.807 I-1.285 J-1.792 E.23897
G1 X194.945 Y112.79 E.00657
M73 P18 R12
G3 X196.639 Y116.469 I.055 J2.204 E.1529
; WIPE_START
M204 S8000
G1 X196.284 Y116.786 E-.18064
G1 X195.909 Y117.015 E-.167
G1 X195.828 Y117.042 E-.03236
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I-1.109 J.502 P1  F60000
G1 X202.79 Y132.416 Z.8
G1 Z.4
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X205.084 Y132.416 E.07376
G1 X205.084 Y141.918 E.30553
G1 X204.889 Y141.958 E.00638
G2 X199.554 Y141.143 I-2.893 J1.066 E.21138
G2 X190.445 Y141.144 I-4.554 J1.862 E.3743
G2 X185.111 Y141.958 I-2.445 J1.866 E.21168
G1 X184.916 Y141.918 E.00639
G1 X184.916 Y132.416 E.30554
G1 X188.416 Y132.416 E.11255
G1 X188.416 Y110.416 E.70744
G1 X201.584 Y110.416 E.42342
G1 X201.584 Y132.416 E.70744
G1 X202.73 Y132.416 E.03686
M204 S10000
G1 X202.79 Y132.009 F60000
G1 F13265.217
M204 S8000
G1 X205.491 Y132.009 E.08685
G1 X205.491 Y149.991 E.57823
G1 X204.909 Y149.991 E.01871
G1 X204.909 Y148.991 E.03216
G1 X204.459 Y148.991 E.01447
G1 X204.459 Y144.008 E.16024
G2 X199.664 Y141.726 I-2.461 J-1.008 E.25915
G1 X199.45 Y142.171 E.01588
G2 X196.855 Y138.89 I-4.576 J.952 E.13947
G2 X190.691 Y141.671 I-1.848 J4.125 E.24566
G1 X190.55 Y142.171 E.0167
G2 X189.213 Y140.632 I-2.759 J1.048 E.06693
G2 X185.541 Y144.012 I-1.212 J2.368 E.20817
G1 X185.541 Y148.991 E.16012
G1 X185.091 Y148.991 E.01447
G1 X185.091 Y149.991 E.03216
G1 X184.509 Y149.991 E.01871
G1 X184.509 Y132.009 E.57823
G1 X188.009 Y132.009 E.11255
G1 X188.009 Y110.009 E.70744
G1 X201.991 Y110.009 E.4496
G1 X201.991 Y132.009 E.70744
G1 X202.73 Y132.009 E.02377
M204 S10000
G1 X202.79 Y131.602 F60000
G1 F13265.217
M204 S8000
G1 X205.898 Y131.602 E.09994
G1 X205.898 Y150.398 E.60441
G1 X204.502 Y150.398 E.04489
G1 X204.502 Y149.398 E.03216
G1 X204.052 Y149.398 E.01447
G1 X204.052 Y143.927 E.17593
G2 X199.948 Y143.924 I-2.052 J-.926 E.28868
G1 X199.948 Y149.398 E.17601
G1 X199.498 Y149.398 E.01447
G1 X199.498 Y150.398 E.03216
G1 X199.102 Y150.398 E.01273
G1 X199.102 Y142.992 E.23814
G2 X190.898 Y142.988 I-4.102 J.009 E.4137
G1 X190.898 Y150.398 E.23827
G1 X190.502 Y150.398 E.01273
G1 X190.502 Y149.398 E.03216
G1 X190.052 Y149.398 E.01447
G1 X190.052 Y143.924 E.17601
G2 X185.948 Y143.924 I-2.052 J-.921 E.28827
G1 X185.948 Y149.398 E.17601
G1 X185.498 Y149.398 E.01447
G1 X185.498 Y150.398 E.03216
G1 X184.102 Y150.398 E.04489
G1 X184.102 Y131.602 E.60441
G1 X187.602 Y131.602 E.11255
G1 X187.602 Y109.602 E.70744
G1 X202.398 Y109.602 E.47578
G1 X202.398 Y131.602 E.70744
G1 X202.73 Y131.602 E.01068
M204 S250
G1 X202.79 Y131.21 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X206.29 Y131.21 E.10425
G1 X206.29 Y150.79 E.58322
G1 X204.11 Y150.79 E.06494
G1 X204.11 Y149.79 E.02979
G1 X203.66 Y149.79 E.0134
G1 X203.66 Y143.836 E.17734
G2 X200.34 Y143.835 I-1.66 J-.831 E.22501
G1 X200.34 Y149.79 E.17737
G1 X199.89 Y149.79 E.0134
G1 X199.89 Y150.79 E.02979
G1 X198.71 Y150.79 E.03515
G1 X198.71 Y142.997 E.23212
G2 X191.29 Y142.996 I-3.71 J.004 E.3469
G1 X191.29 Y150.79 E.23216
G1 X190.11 Y150.79 E.03515
G1 X190.11 Y149.79 E.02979
G1 X189.66 Y149.79 E.0134
G1 X189.66 Y143.835 E.17737
G2 X186.34 Y143.835 I-1.66 J-.833 E.22525
G1 X186.34 Y149.79 E.17737
G1 X185.89 Y149.79 E.0134
G1 X185.89 Y150.79 E.02979
G1 X183.71 Y150.79 E.06494
G1 X183.71 Y131.21 E.58322
G1 X187.21 Y131.21 E.10425
G1 X187.21 Y109.21 E.65531
G1 X202.79 Y109.21 E.46408
G1 X202.79 Y131.15 E.65352
; WIPE_START
M204 S8000
G1 X203.79 Y131.167 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I-1.215 J.064 P1  F60000
G1 X204.297 Y140.733 Z.8
G1 Z.4
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42259
G1 F14222.878
M204 S8000
G1 X204.751 Y140.28 E.01922
G1 X204.751 Y139.743 E.0161
G1 X204.132 Y140.361 E.02624
G2 X203.82 Y140.137 I-.881 J.897 E.01158
G1 X204.751 Y139.206 E.03949
G1 X204.751 Y138.669 E.0161
G1 X203.479 Y139.94 E.05393
G2 X203.098 Y139.785 I-.967 J1.828 E.01238
G1 X204.751 Y138.132 E.07011
G1 X204.751 Y137.595 E.0161
G1 X202.67 Y139.675 E.08823
G2 X202.2 Y139.608 I-.505 J1.861 E.01427
G1 X204.751 Y137.058 E.10816
G1 X204.751 Y136.521 E.0161
G1 X201.652 Y139.62 E.13143
G2 X200.974 Y139.761 I.376 J3.504 E.0208
G1 X204.751 Y135.984 E.16018
G1 X204.751 Y135.447 E.0161
G1 X199.64 Y140.556 E.21672
G2 X199.447 Y140.214 I-1.806 J.793 E.0118
G1 X204.751 Y134.91 E.22495
G1 X204.751 Y134.373 E.0161
G1 X199.229 Y139.894 E.23418
G2 X198.993 Y139.594 I-3.608 J2.593 E.01147
G1 X204.751 Y133.836 E.2442
G1 X204.751 Y133.299 E.0161
G1 X198.735 Y139.315 E.25516
G2 X198.46 Y139.053 I-3.616 J3.497 E.01139
G1 X204.751 Y132.749 E.26706
G1 X204.227 Y132.749 E.01571
G1 X198.162 Y138.814 E.25723
G2 X197.849 Y138.59 I-1.648 J1.97 E.01155
G1 X203.69 Y132.749 E.24773
G1 X203.153 Y132.749 E.0161
G1 X197.509 Y138.393 E.23938
G2 X197.153 Y138.212 I-1.394 J2.293 E.01198
G1 X202.616 Y132.749 E.23169
G1 X202.079 Y132.749 E.0161
G1 X196.767 Y138.062 E.22531
G2 X196.361 Y137.931 I-1.075 J2.636 E.0128
G1 X201.542 Y132.749 E.21975
G1 X201.251 Y132.749 E.00874
G1 X201.251 Y132.504 E.00736
G1 X195.917 Y137.837 E.2262
G2 X195.443 Y137.774 I-.556 J2.379 E.01437
G1 X201.251 Y131.967 E.24632
G1 X201.251 Y131.43 E.0161
G1 X194.929 Y137.752 E.26812
G2 X194.354 Y137.79 I-.032 J3.86 E.01731
G1 X201.251 Y130.893 E.29252
G1 X201.251 Y130.356 E.0161
G1 X193.684 Y137.923 E.32093
G2 X192.865 Y138.205 I1.001 J4.239 E.02601
G1 X201.251 Y129.819 E.35566
G1 X201.251 Y129.282 E.0161
G1 X190.157 Y140.376 E.47053
G2 X189.85 Y140.146 I-1.111 J1.161 E.01153
G1 X201.251 Y128.745 E.48354
G1 X201.251 Y128.208 E.0161
G1 X189.506 Y139.952 E.49811
G2 X189.127 Y139.795 I-.977 J1.812 E.01234
G1 X201.251 Y127.671 E.51419
G1 X201.251 Y127.135 E.0161
G1 X188.703 Y139.682 E.53217
G2 X188.233 Y139.615 I-.45 J1.489 E.01431
G1 X201.251 Y126.598 E.55213
G1 X201.251 Y126.061 E.0161
G1 X187.695 Y139.616 E.57493
G2 X187.031 Y139.743 I.32 J3.462 E.02032
G1 X201.251 Y125.524 E.60311
G1 X201.251 Y124.987 E.0161
G1 X185.942 Y140.295 E.64928
G2 X185.345 Y140.883 I2.091 J2.719 E.0252
G1 X185.249 Y140.807 E.00368
G1 X185.249 Y140.451 E.01068
G1 X201.251 Y124.45 E.67867
G1 X201.251 Y123.913 E.0161
G1 X185.249 Y139.914 E.67867
G1 X185.249 Y139.377 E.0161
G1 X201.251 Y123.376 E.67867
G1 X201.251 Y122.839 E.0161
G1 X185.249 Y138.84 E.67867
G1 X185.249 Y138.303 E.0161
G1 X201.251 Y122.302 E.67867
G1 X201.251 Y121.765 E.0161
G1 X185.249 Y137.766 E.67867
G1 X185.249 Y137.229 E.0161
G1 X201.251 Y121.228 E.67867
G1 X201.251 Y120.691 E.0161
G1 X185.249 Y136.692 E.67867
M73 P19 R12
G1 X185.249 Y136.155 E.0161
G1 X201.251 Y120.154 E.67867
G1 X201.251 Y119.617 E.0161
G1 X188.749 Y132.119 E.53022
G1 X188.749 Y131.582 E.0161
G1 X201.251 Y119.081 E.53022
G1 X201.251 Y118.544 E.0161
G1 X188.749 Y131.045 E.53022
G1 X188.749 Y130.508 E.0161
G1 X201.251 Y118.007 E.53022
G1 X201.251 Y117.47 E.0161
G1 X188.749 Y129.971 E.53022
G1 X188.749 Y129.434 E.0161
G1 X201.251 Y116.933 E.53022
G1 X201.251 Y116.396 E.0161
G1 X188.749 Y128.897 E.53022
G1 X188.749 Y128.36 E.0161
G1 X201.251 Y115.859 E.53022
G1 X201.251 Y115.322 E.0161
G1 X188.749 Y127.823 E.53022
G1 X188.749 Y127.286 E.0161
G1 X201.251 Y114.785 E.53022
G1 X201.251 Y114.248 E.0161
G1 X188.749 Y126.749 E.53022
G1 X188.749 Y126.212 E.0161
G1 X196.542 Y118.42 E.33049
G3 X195.753 Y118.672 I-1.685 J-3.916 E.02487
G1 X188.749 Y125.675 E.29704
G1 X188.749 Y125.138 E.0161
G1 X195.141 Y118.747 E.27109
G3 X194.622 Y118.729 I-.095 J-4.748 E.01558
G1 X188.749 Y124.601 E.24908
G1 X188.749 Y124.065 E.0161
G1 X194.162 Y118.652 E.22957
G3 X193.746 Y118.531 I.393 J-2.135 E.01302
G1 X188.749 Y123.528 E.21191
G1 X188.749 Y122.991 E.0161
G1 X193.366 Y118.374 E.19583
G3 X193.02 Y118.183 I.779 J-1.83 E.01188
G1 X188.749 Y122.454 E.18112
G1 X188.749 Y121.917 E.0161
G1 X192.703 Y117.963 E.16768
G3 X192.414 Y117.715 I1.098 J-1.571 E.01144
G1 X188.749 Y121.38 E.15543
G1 X188.749 Y120.843 E.0161
G1 X192.152 Y117.44 E.14433
G3 X191.918 Y117.137 I1.392 J-1.319 E.0115
G1 X188.749 Y120.306 E.1344
G1 X188.749 Y119.769 E.0161
G1 X191.712 Y116.806 E.12567
G3 X191.538 Y116.444 I12.62 J-6.299 E.01206
G1 X188.749 Y119.232 E.11827
G1 X188.749 Y118.695 E.0161
G1 X191.4 Y116.045 E.1124
G3 X191.302 Y115.606 I2.15 J-.708 E.01352
G1 X188.749 Y118.158 E.10826
G1 X188.749 Y117.621 E.0161
G1 X191.254 Y115.117 E.10623
G3 X191.281 Y114.553 I3.618 J-.11 E.01695
G1 X188.749 Y117.084 E.10738
G1 X188.749 Y116.547 E.0161
G1 X191.716 Y113.581 E.12583
; WIPE_START
G1 X191.009 Y114.288 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I1.111 J-.498 P1  F60000
G1 X189.348 Y110.58 Z.8
G1 Z.4
G1 E.4 F1800
G1 F14222.878
M204 S8000
G1 X188.749 Y111.178 E.02538
G1 X188.749 Y111.715 E.0161
G1 X189.715 Y110.749 E.04095
G1 X190.252 Y110.749 E.0161
G1 X188.749 Y112.252 E.06373
G1 X188.749 Y112.789 E.0161
G1 X190.789 Y110.749 E.0865
G1 X191.326 Y110.749 E.0161
G1 X188.749 Y113.326 E.10928
G1 X188.749 Y113.863 E.0161
G1 X191.863 Y110.749 E.13205
G1 X192.4 Y110.749 E.0161
G1 X188.749 Y114.4 E.15482
G1 X188.749 Y114.937 E.0161
G1 X192.937 Y110.749 E.1776
G1 X193.474 Y110.749 E.0161
G1 X188.749 Y115.474 E.20037
G1 X188.749 Y116.011 E.0161
G1 X194.011 Y110.749 E.22314
G1 X194.547 Y110.749 E.0161
G1 X193.872 Y111.425 E.02865
G3 X194.558 Y111.276 I1.356 J4.584 E.02108
G1 X195.084 Y110.749 E.02232
G1 X195.621 Y110.749 E.0161
G1 X195.116 Y111.255 E.02143
G3 X195.608 Y111.3 I.02 J2.48 E.01484
G1 X196.158 Y110.749 E.02335
G1 X196.695 Y110.749 E.0161
G1 X196.046 Y111.399 E.02753
G3 X196.442 Y111.54 I-.507 J2.047 E.01262
G1 X197.232 Y110.749 E.03352
G1 X197.769 Y110.749 E.0161
G1 X196.804 Y111.715 E.04094
G3 X197.135 Y111.92 I-.859 J1.755 E.01172
G1 X198.306 Y110.749 E.04966
G1 X198.843 Y110.749 E.0161
G1 X197.438 Y112.154 E.05958
G3 X197.714 Y112.416 I-1.171 J1.51 E.01141
G1 X199.38 Y110.749 E.07067
G1 X199.917 Y110.749 E.0161
G1 X197.962 Y112.704 E.08292
G3 X198.182 Y113.021 I-1.47 J1.257 E.01159
G1 X200.454 Y110.749 E.09635
G1 X200.991 Y110.749 E.0161
G1 X198.373 Y113.367 E.11104
G3 X198.531 Y113.746 I-1.807 J.979 E.01233
G1 X201.251 Y111.027 E.11535
G1 X201.251 Y111.563 E.0161
G1 X198.653 Y114.161 E.11018
G3 X198.732 Y114.619 I-2.249 J.624 E.01396
G1 X201.251 Y112.1 E.10683
G1 X201.251 Y112.637 E.0161
G1 X198.742 Y115.146 E.10639
G3 X198.665 Y115.76 I-2.462 J.003 E.01861
G1 X201.251 Y113.174 E.10966
G1 X201.251 Y113.711 E.0161
G1 X197.975 Y116.986 E.13892
; WIPE_START
G1 X198.682 Y116.279 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I-.946 J-.765 P1  F60000
G1 X185.08 Y133.104 Z.8
G1 Z.4
G1 E.4 F1800
G1 F14222.878
M204 S8000
G1 X185.434 Y132.749 E.01502
G1 X185.971 Y132.749 E.0161
G1 X185.249 Y133.471 E.0306
G1 X185.249 Y134.008 E.0161
G1 X186.508 Y132.749 E.05337
G1 X187.045 Y132.749 E.0161
G1 X185.249 Y134.545 E.07614
G1 X185.249 Y135.082 E.0161
G1 X187.582 Y132.749 E.09892
G1 X188.119 Y132.749 E.0161
G1 X185.08 Y135.788 E.12889
; WIPE_START
G1 X185.787 Y135.081 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I-1.212 J-.11 P1  F60000
G1 X185.23 Y141.218 Z.8
G1 Z.4
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.10481
G1 F15000
M204 S8000
G1 X185.182 Y141.278 E.00037
G2 X185.14 Y141.377 I.105 J.103 E.00054
M204 S10000
G1 X185.247 Y142.195 F60000
; LINE_WIDTH: 0.51098
G1 F11536.997
M204 S8000
G1 X184.954 Y142.394 E.0131
G2 X184.932 Y142.692 I6.834 J.655 E.01105
; LINE_WIDTH: 0.477543
G1 F12424.571
G1 X184.926 Y142.913 E.00761
G2 X184.942 Y143.47 I8.969 J.008 E.01911
; LINE_WIDTH: 0.516372
G1 F11405.6
G1 X184.956 Y143.612 E.00535
; LINE_WIDTH: 0.54742
G1 F10703.682
G1 X184.974 Y143.78 E.00675
; LINE_WIDTH: 0.585685
G1 F9949.061
G1 X184.994 Y143.916 E.00586
; LINE_WIDTH: 0.629774
G1 F9201.615
G1 X185.018 Y144.074 E.00741
; LINE_WIDTH: 0.66753
G1 F8645.403
G1 X185.025 Y148.787 E.23258
; WIPE_START
G1 X185.024 Y147.787 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I-.304 J1.178 P1  F60000
G1 X190.475 Y149.194 Z.8
G1 Z.4
G1 E.4 F1800
; LINE_WIDTH: 0.481259
G1 F12319.231
M204 S8000
G1 X190.475 Y144.013 E.17942
G1 X190.496 Y143.901 E.00395
; LINE_WIDTH: 0.419069
G1 F14356.043
G1 X190.516 Y143.773 E.00385
; LINE_WIDTH: 0.382954
G1 F15000
G1 X190.533 Y143.661 E.00305
; LINE_WIDTH: 0.348623
G1 X190.55 Y143.509 E.0037
; LINE_WIDTH: 0.304476
G1 X190.574 Y143.126 E.00792
; LINE_WIDTH: 0.282046
G1 X190.574 Y142.984 E.00268
G3 X190.601 Y142.829 I.311 J-.026 E.00301
; LINE_WIDTH: 0.21819
G1 X190.626 Y142.793 E.0006
; LINE_WIDTH: 0.171032
G1 X190.651 Y142.758 E.00044
; LINE_WIDTH: 0.14208
G1 X190.658 Y142.713 E.00036
; LINE_WIDTH: 0.11413
G1 X190.703 Y142.473 E.00137
; WIPE_START
G1 X190.658 Y142.713 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I-.718 J.982 P1  F60000
G1 X199.525 Y149.194 Z.8
G1 Z.4
G1 E.4 F1800
; LINE_WIDTH: 0.48126
G1 F12319.211
M204 S8000
G1 X199.525 Y144.013 E.17942
G1 X199.504 Y143.901 E.00394
; LINE_WIDTH: 0.418334
G1 F14384.137
G1 X199.483 Y143.768 E.00399
; LINE_WIDTH: 0.380693
G1 F15000
G1 X199.466 Y143.651 E.00317
; LINE_WIDTH: 0.361082
G1 X199.464 Y143.635 E.0004
; LINE_WIDTH: 0.334785
G1 X199.439 Y143.39 E.00566
; LINE_WIDTH: 0.297509
G1 X199.427 Y143.142 E.005
; LINE_WIDTH: 0.281996
G1 X199.425 Y142.99 E.00287
G3 X199.45 Y142.822 I.544 J-.006 E.00322
; LINE_WIDTH: 0.226991
G1 X199.473 Y142.779 E.00071
; LINE_WIDTH: 0.201873
G1 X199.478 Y142.76 E.00025
; LINE_WIDTH: 0.173392
G1 X199.52 Y142.615 E.00155
; LINE_WIDTH: 0.135646
G1 X199.559 Y142.502 E.00088
; LINE_WIDTH: 0.109684
G1 X199.596 Y142.391 E.00061
; WIPE_START
G1 X199.559 Y142.502 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I.291 J1.182 P1  F60000
G1 X204.77 Y141.217 Z.8
G1 Z.4
G1 E.4 F1800
; LINE_WIDTH: 0.104868
G1 F15000
M204 S8000
G3 X204.86 Y141.377 I-.202 J.22 E.00091
M204 S10000
G1 X204.753 Y142.195 F60000
; LINE_WIDTH: 0.511746
G1 F11518.133
M204 S8000
G1 X205.045 Y142.382 E.01284
G1 X205.067 Y142.676 E.01092
; LINE_WIDTH: 0.476969
G1 F12440.999
G3 X205.059 Y143.446 I-6.898 J.317 E.02644
; LINE_WIDTH: 0.514178
G1 F11458.689
G1 X205.044 Y143.612 E.00619
; LINE_WIDTH: 0.544761
G1 F10760.392
G1 X205.029 Y143.755 E.00569
; LINE_WIDTH: 0.582818
G1 F10001.892
G1 X205.005 Y143.921 E.00719
; LINE_WIDTH: 0.628923
G1 F9214.982
G1 X204.984 Y144.062 E.0066
; LINE_WIDTH: 0.667488
G1 F8645.979
G1 X204.975 Y148.787 E.23311
; OBJECT_ID: 8
; WIPE_START
G1 X204.977 Y147.787 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 12
M625
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z.8 I.552 J-1.085 P1  F60000
G1 X141.883 Y115.684 Z.8
G1 Z.4
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X141.883 Y174.884 E1.90366
G1 X140.117 Y174.884 E.0568
G1 X140.117 Y115.684 E1.90366
G1 X121.416 Y115.684 E.60135
G1 X121.416 Y113.516 E.0697
G1 X157.584 Y113.516 E1.16302
G1 X157.584 Y115.684 E.0697
G1 X155.883 Y115.684 E.05469
G1 X155.883 Y174.884 E1.90366
G1 X154.117 Y174.884 E.0568
G1 X154.117 Y115.684 E1.90366
G1 X141.943 Y115.684 E.39146
M204 S10000
G1 X142.29 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X142.29 Y175.291 E1.90366
G1 X141.39 Y175.291 E.02893
G1 X141.39 Y185.682 E.33414
G1 X141 Y186.073 E.01776
G1 X140.61 Y185.682 E.01776
G1 X140.61 Y175.291 E.33414
G1 X139.71 Y175.291 E.02893
G1 X139.71 Y116.091 E1.90366
G1 X121.009 Y116.091 E.60135
G1 X121.009 Y113.109 E.09588
G1 X157.991 Y113.109 E1.1892
G1 X157.991 Y116.091 E.09588
G1 X156.29 Y116.091 E.05469
G1 X156.29 Y175.291 E1.90366
G1 X155.39 Y175.291 E.02893
G1 X155.39 Y185.682 E.33414
M73 P20 R12
G1 X155 Y186.073 E.01776
G1 X154.61 Y185.682 E.01776
G1 X154.61 Y175.291 E.33414
G1 X153.71 Y175.291 E.02893
G1 X153.71 Y116.091 E1.90366
G1 X142.35 Y116.091 E.36528
M204 S10000
G1 X142.697 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X142.697 Y174.902 E1.87806
G1 X143.298 Y174.902 E.01931
G1 X143.298 Y175.698 E.02559
G1 X141.798 Y175.698 E.04824
G1 X141.798 Y185.851 E.32647
G1 X141.498 Y186.151 E.01364
G1 X141.498 Y187.023 E.02806
G1 X141.177 Y187.298 E.01357
G1 X140.823 Y187.298 E.0114
G1 X140.502 Y187.023 E.01357
G1 X140.502 Y186.151 E.02806
G1 X140.202 Y185.851 E.01364
G1 X140.202 Y175.698 E.32647
G1 X138.702 Y175.698 E.04824
G1 X138.702 Y174.902 E.02559
G1 X139.303 Y174.902 E.01931
G1 X139.303 Y116.498 E1.87806
G1 X120.602 Y116.498 E.60135
G1 X120.602 Y112.702 E.12206
G1 X158.398 Y112.702 E1.21538
G1 X158.398 Y116.498 E.12206
G1 X156.697 Y116.498 E.05469
G1 X156.697 Y174.902 E1.87806
G1 X157.298 Y174.902 E.01931
G1 X157.298 Y175.698 E.02559
G1 X155.798 Y175.698 E.04824
G1 X155.798 Y185.851 E.32647
G1 X155.498 Y186.151 E.01364
G1 X155.498 Y186.523 E.01198
G1 X155.177 Y186.798 E.01357
G1 X154.823 Y186.798 E.0114
G1 X154.502 Y186.523 E.01357
G1 X154.502 Y186.151 E.01198
G1 X154.202 Y185.851 E.01364
G1 X154.202 Y175.698 E.32647
G1 X152.702 Y175.698 E.04824
G1 X152.702 Y174.902 E.02559
G1 X153.303 Y174.902 E.01931
G1 X153.303 Y116.498 E1.87806
G1 X142.757 Y116.498 E.3391
M204 S250
G1 X143.089 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X143.089 Y174.51 E1.7163
G1 X143.69 Y174.51 E.01788
G1 X143.69 Y176.09 E.04706
G1 X142.19 Y176.09 E.04468
G1 X142.19 Y186.013 E.29557
G1 X141.89 Y186.313 E.01264
G1 X141.89 Y187.203 E.02652
G1 X141.322 Y187.69 E.02226
G1 X140.678 Y187.69 E.0192
G1 X140.11 Y187.203 E.02226
G1 X140.11 Y186.313 E.02652
G1 X139.81 Y186.013 E.01264
G1 X139.81 Y176.09 E.29557
G1 X138.31 Y176.09 E.04468
G1 X138.31 Y174.51 E.04706
G1 X138.911 Y174.51 E.01788
G1 X138.911 Y116.89 E1.7163
G1 X120.21 Y116.89 E.55703
G1 X120.21 Y112.31 E.13642
G1 X158.79 Y112.31 E1.14917
G1 X158.79 Y116.89 E.13642
G1 X157.089 Y116.89 E.05066
G1 X157.089 Y174.51 E1.7163
G1 X157.69 Y174.51 E.01788
G1 X157.69 Y176.09 E.04706
G1 X156.19 Y176.09 E.04468
G1 X156.19 Y186.013 E.29557
G1 X155.89 Y186.313 E.01264
G1 X155.89 Y186.703 E.01163
G1 X155.322 Y187.19 E.02226
G1 X154.678 Y187.19 E.0192
G1 X154.11 Y186.703 E.02226
G1 X154.11 Y186.313 E.01163
G1 X153.81 Y186.013 E.01264
G1 X153.81 Y176.09 E.29557
G1 X152.31 Y176.09 E.04468
G1 X152.31 Y174.51 E.04706
G1 X152.911 Y174.51 E.01788
G1 X152.911 Y116.89 E1.7163
G1 X143.149 Y116.89 E.29075
; WIPE_START
M204 S8000
G1 X143.148 Y117.89 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I.318 J1.175 P1  F60000
G1 X155.032 Y114.675 Z.8
G1 Z.4
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.55754
G1 F10493.18
M204 S8000
G2 X155.034 Y114.783 I-.027 J.054 E.01014
; WIPE_START
G1 X154.968 Y114.787 E-.09748
G1 X154.936 Y114.731 E-.09417
G1 X154.968 Y114.675 E-.09417
G1 X155.032 Y114.675 E-.09418
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I0 J-1.217 P1  F60000
G1 X141.032 Y114.675 Z.8
G1 Z.4
G1 E.4 F1800
G1 F10493.18
M204 S8000
G2 X141.034 Y114.783 I-.027 J.054 E.01014
M204 S10000
G1 X141 Y115.48 F60000
; LINE_WIDTH: 0.625235
G1 F9273.332
M204 S8000
G1 X141.06 Y115.396 E.00474
; LINE_WIDTH: 0.579625
G1 F10061.394
G1 X141.12 Y115.313 E.00437
; LINE_WIDTH: 0.534015
G1 F10995.836
G1 X141.18 Y115.229 E.004
; LINE_WIDTH: 0.488405
G1 F12121.62
G1 X141.24 Y115.145 E.00362
; LINE_WIDTH: 0.442795
G1 F13504.22
G1 X141.3 Y115.061 E.00325
; LINE_WIDTH: 0.442124
G1 F13526.941
G1 X141.39 Y114.994 E.00356
; LINE_WIDTH: 0.48639
G1 F12176.697
G1 X141.48 Y114.926 E.00396
; LINE_WIDTH: 0.546013
G1 F10733.611
G3 X141.68 Y114.852 I.155 J.113 E.00896
G1 X154.32 Y114.852 E.50235
; LINE_WIDTH: 0.525099
G1 F11199.176
G1 X154.447 Y114.922 E.00551
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X154.574 Y114.991 E.00503
; LINE_WIDTH: 0.441012
G1 F13564.713
G1 X154.7 Y115.061 E.00455
; LINE_WIDTH: 0.442795
G1 F13504.22
G1 X154.76 Y115.145 E.00325
; LINE_WIDTH: 0.488405
G1 F12121.62
G1 X154.82 Y115.229 E.00362
; LINE_WIDTH: 0.534015
G1 F10995.836
G1 X154.88 Y115.313 E.004
; LINE_WIDTH: 0.579625
G1 F10061.394
G1 X154.94 Y115.396 E.00437
; LINE_WIDTH: 0.625235
G1 F9273.332
G1 X155 Y115.48 E.00474
G1 X155.06 Y115.396 E.00474
; LINE_WIDTH: 0.579625
G1 F10061.394
G1 X155.12 Y115.313 E.00437
; LINE_WIDTH: 0.534015
G1 F10995.836
G1 X155.18 Y115.229 E.004
; LINE_WIDTH: 0.488405
G1 F12121.62
G1 X155.24 Y115.145 E.00362
; LINE_WIDTH: 0.442795
G1 F13504.22
G1 X155.3 Y115.061 E.00325
; LINE_WIDTH: 0.442124
G1 F13526.941
G1 X155.39 Y114.994 E.00356
; LINE_WIDTH: 0.48639
G1 F12176.697
G1 X155.48 Y114.926 E.00396
; LINE_WIDTH: 0.546592
G1 F10721.27
G1 X155.57 Y114.858 E.00449
G3 X156.752 Y114.852 I1.055 J89.117 E.047
G1 X156.752 Y114.348 E.02002
G1 X155.68 Y114.348 E.04265
; LINE_WIDTH: 0.525099
G1 F11199.176
G1 X155.453 Y114.327 E.00867
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X155.227 Y114.306 E.00791
; LINE_WIDTH: 0.441012
G1 F13564.713
G1 X155 Y114.285 E.00715
G1 X154.773 Y114.306 E.00715
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X154.547 Y114.327 E.00791
; LINE_WIDTH: 0.545749
G1 F10739.253
G1 X154.32 Y114.348 E.00904
G1 X141.68 Y114.348 E.50209
; LINE_WIDTH: 0.525099
G1 F11199.176
G1 X141.453 Y114.327 E.00867
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X141.227 Y114.306 E.00791
; LINE_WIDTH: 0.441012
G1 F13564.713
G1 X141 Y114.285 E.00715
G1 X140.773 Y114.306 E.00715
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X140.547 Y114.327 E.00791
; LINE_WIDTH: 0.545991
G1 F10734.087
G1 X140.32 Y114.348 E.00904
G1 X122.248 Y114.348 E.71816
G1 X122.248 Y114.852 E.02
G1 X140.32 Y114.852 E.71816
; LINE_WIDTH: 0.525099
G1 F11199.176
G1 X140.447 Y114.922 E.00551
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X140.574 Y114.991 E.00503
; LINE_WIDTH: 0.441012
G1 F13564.713
G1 X140.7 Y115.061 E.00455
; LINE_WIDTH: 0.442795
G1 F13504.22
G1 X140.753 Y115.135 E.00287
; LINE_WIDTH: 0.488405
G1 F12121.62
G1 X140.806 Y115.209 E.0032
; LINE_WIDTH: 0.534015
G1 F10995.836
G1 X140.859 Y115.283 E.00353
; LINE_WIDTH: 0.579625
G1 F10061.394
G1 X140.912 Y115.357 E.00386
; LINE_WIDTH: 0.625235
G1 F9273.332
G1 X140.965 Y115.431 E.00419
; WIPE_START
G1 X140.912 Y115.357 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I-1.217 J-.008 P1  F60000
G1 X140.509 Y174.492 Z.8
G1 Z.4
G1 E.4 F1800
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X141.491 Y174.492 E.02926
G1 X141.491 Y115.48 E1.75771
G1 X141.553 Y115.341 E.00455
G1 X141.68 Y115.292 E.00404
G1 X154.32 Y115.292 E.37651
G1 X154.485 Y115.389 E.00571
G1 X154.509 Y115.48 E.0028
G1 X154.509 Y174.492 E1.75771
G1 X155.491 Y174.492 E.02926
G1 X155.491 Y115.48 E1.75771
G1 X155.553 Y115.341 E.00455
G1 X155.68 Y115.292 E.00404
G1 X157.192 Y115.292 E.04504
G1 X157.192 Y113.908 E.04121
G1 X121.808 Y113.908 E1.05393
G1 X121.808 Y115.292 E.04121
G1 X140.32 Y115.292 E.5514
G1 X140.485 Y115.389 E.00571
G1 X140.509 Y115.48 E.0028
G1 X140.509 Y174.432 E1.75592
M204 S10000
G1 X141 Y174.001 F60000
; LINE_WIDTH: 0.64804
G1 F8923.85
M204 S8000
G1 X141 Y115.54 E2.79441
; WIPE_START
G1 X141 Y116.54 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I-1.182 J.288 P1  F60000
G1 X155 Y174.001 Z.8
G1 Z.4
M73 P21 R12
G1 E.4 F1800
; LINE_WIDTH: 0.64805
G1 F8923.703
M204 S8000
G1 X155 Y115.54 E2.79446
; WIPE_START
G1 X155 Y116.54 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I-1.217 J0 P1  F60000
G1 X155 Y175.087 Z.8
G1 Z.4
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.41678
G1 F14443.909
M204 S8000
G1 X155 Y185.785 E.31591
M204 S10000
G1 X155.294 Y186.254 F60000
; LINE_WIDTH: 0.290873
G1 F15000
M204 S8000
G3 X155.056 Y186.471 I-1.487 J-1.397 E.00631
G1 X154.944 Y186.471 E.0022
G3 X154.706 Y186.254 I1.252 J-1.616 E.0063
; WIPE_START
G1 X154.944 Y186.471 E-.16177
G1 X155.056 Y186.471 E-.05645
G1 X155.294 Y186.254 E-.16178
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I.04 J-1.216 P1  F60000
G1 X141 Y185.785 Z.8
G1 Z.4
G1 E.4 F1800
; LINE_WIDTH: 0.41678
G1 F14443.909
M204 S8000
G1 X141 Y175.087 E.31591
; WIPE_START
G1 X141 Y176.087 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I1.115 J-.488 P1  F60000
G1 X114.584 Y115.684 Z.8
G1 Z.4
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X112.416 Y115.684 E.0697
G1 X112.416 Y113.516 E.0697
G1 X114.584 Y113.516 E.0697
G1 X114.584 Y115.624 E.06777
M204 S10000
G1 X114.991 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X112.009 Y116.091 E.09588
G1 X112.009 Y113.109 E.09588
G1 X114.991 Y113.109 E.09588
G1 X114.991 Y116.031 E.09395
M204 S10000
G1 X115.398 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X111.602 Y116.498 E.12206
G1 X111.602 Y112.702 E.12206
G1 X115.398 Y112.702 E.12206
G1 X115.398 Y116.438 E.12013
M204 S250
G1 X115.79 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X111.21 Y116.89 E.13642
G1 X111.21 Y112.31 E.13642
G1 X115.79 Y112.31 E.13642
G1 X115.79 Y116.83 E.13464
; WIPE_START
M204 S8000
G1 X114.79 Y116.843 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z.8 I1.135 J-.438 P1  F60000
G1 X114.192 Y115.292 Z.8
G1 Z.4
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X114.192 Y113.908 E.04121
G1 X112.808 Y113.908 E.04121
G1 X112.808 Y115.292 E.04121
G1 X114.132 Y115.292 E.03942
M204 S10000
G1 X113.752 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X113.752 Y114.348 E.02
G1 X113.248 Y114.348 E.02
G1 X113.248 Y114.852 E.02
G1 X113.692 Y114.852 E.01762
; CHANGE_LAYER
; Z_HEIGHT: 0.6
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F10731.32
G1 X113.248 Y114.852 E-.16842
G1 X113.248 Y114.348 E-.19122
G1 X113.302 Y114.348 E-.02037
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 3/27
; update layer progress
M73 L3
M991 S0 P2 ;notify layer change
; OBJECT_ID: 16
; COOLING_NODE: 0
; start printing object, unique label id: 16
M624 BAAAAAAAAAA=
M204 S10000
G17
G3 Z.8 I-.751 J.958 P1  F60000
G1 X194.975 Y178.414 Z.8
G1 Z.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X194.745 Y178.404 E.00739
G3 X194.575 Y171.609 I.255 J-3.406 E.32317
G1 X194.915 Y171.583 E.01097
G3 X195.085 Y178.413 I.085 J3.415 E.34506
G1 X195.035 Y178.413 E.00162
; COOLING_NODE: 0
M204 S10000
G1 X194.985 Y178.007 F60000
G1 F13265.217
M204 S8000
G1 X194.775 Y177.998 E.00674
G3 X194.625 Y172.013 I.225 J-3 E.28463
G1 X194.925 Y171.991 E.00966
G3 X195.075 Y178.006 I.075 J3.008 E.30392
G1 X195.045 Y178.006 E.00097
; COOLING_NODE: 0
M204 S10000
G1 X194.995 Y177.6 F60000
G1 F13265.217
M204 S8000
G1 X194.806 Y177.592 E.00609
G3 X194.676 Y172.417 I.194 J-2.594 E.24609
G1 X194.935 Y172.398 E.00835
G3 X195.065 Y177.599 I.065 J2.6 E.26277
G1 X195.055 Y177.599 E.00032
; COOLING_NODE: 0
M204 S250
G1 X195.006 Y177.206 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X194.617 Y177.174 E.01164
G3 X194.725 Y172.807 I.383 J-2.175 E.18703
G1 X194.945 Y172.79 E.00657
G3 X195.066 Y177.207 I.055 J2.208 E.20636
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X194.617 Y177.174 E-.17127
G1 X194.193 Y177.057 E-.16718
G1 X194.095 Y177.008 E-.04155
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I-1.06 J.598 P1  F60000
G1 X202.79 Y192.416 Z1
G1 Z.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X205.084 Y192.416 E.07376
G1 X205.084 Y201.923 E.3057
G1 X204.888 Y201.963 E.00642
G2 X199.556 Y201.147 I-2.888 J1.045 E.21173
G2 X190.449 Y201.135 I-4.556 J1.861 E.37401
G2 X185.173 Y201.808 I-2.439 J1.898 E.20599
G1 X185.118 Y201.959 E.00516
G1 X184.916 Y201.924 E.00659
G1 X184.916 Y192.416 E.30573
G1 X188.416 Y192.416 E.11255
G1 X188.416 Y170.416 E.70744
G1 X201.584 Y170.416 E.42342
G1 X201.584 Y192.416 E.70744
G1 X202.73 Y192.416 E.03686
; COOLING_NODE: 0
M204 S10000
G1 X202.79 Y192.009 F60000
G1 F13265.217
M204 S8000
G1 X205.491 Y192.009 E.08685
G1 X205.491 Y209.991 E.57823
G1 X204.909 Y209.991 E.01871
G1 X204.909 Y208.991 E.03216
G1 X204.659 Y208.991 E.00804
G1 X204.659 Y202.975 E.19344
G2 X199.658 Y201.739 I-2.66 J.027 E.22555
G1 X199.45 Y202.171 E.01543
G2 X196.855 Y198.89 I-4.576 J.952 E.13949
G2 X190.615 Y201.941 I-1.853 J4.117 E.25486
G1 X190.442 Y201.952 E.00557
G2 X185.341 Y202.975 I-2.441 J1.058 E.23264
G1 X185.341 Y208.991 E.19344
G1 X185.091 Y208.991 E.00804
G1 X185.091 Y209.991 E.03216
G1 X184.509 Y209.991 E.01871
G1 X184.509 Y192.009 E.57823
G1 X188.009 Y192.009 E.11255
G1 X188.009 Y170.009 E.70744
G1 X201.991 Y170.009 E.4496
G1 X201.991 Y192.009 E.70744
G1 X202.73 Y192.009 E.02377
; COOLING_NODE: 0
M204 S10000
G1 X202.79 Y191.602 F60000
G1 F13265.217
M204 S8000
G1 X205.898 Y191.602 E.09994
G1 X205.898 Y210.398 E.60441
G1 X204.502 Y210.398 E.04489
G1 X204.502 Y209.398 E.03216
G1 X204.252 Y209.398 E.00804
G1 X204.252 Y202.985 E.20621
G2 X199.748 Y202.985 I-2.252 J.021 E.22618
G1 X199.748 Y209.398 E.20621
G1 X199.498 Y209.398 E.00804
G1 X199.498 Y210.398 E.03216
G1 X199.102 Y210.398 E.01273
G1 X199.102 Y202.992 E.23814
G2 X190.898 Y202.992 I-4.102 J.01 E.41374
G1 X190.898 Y210.398 E.23814
G1 X190.502 Y210.398 E.01273
G1 X190.502 Y209.398 E.03216
G1 X190.252 Y209.398 E.00804
G1 X190.252 Y202.985 E.20621
G2 X185.748 Y202.985 I-2.252 J.021 E.22618
G1 X185.748 Y209.398 E.20621
G1 X185.498 Y209.398 E.00804
G1 X185.498 Y210.398 E.03216
G1 X184.102 Y210.398 E.04489
G1 X184.102 Y191.602 E.60441
G1 X187.602 Y191.602 E.11255
G1 X187.602 Y169.602 E.70744
G1 X202.398 Y169.602 E.47578
G1 X202.398 Y191.602 E.70744
G1 X202.73 Y191.602 E.01068
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y191.21 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X206.29 Y191.21 E.10425
G1 X206.29 Y210.79 E.58322
; object ids of layer 3 start: 8,12,16
M624 BwAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer3 end: 8,12,16
M625
G1 X204.11 Y210.79 E.06494
G1 X204.11 Y209.79 E.02979
G1 X203.86 Y209.79 E.00745
G1 X203.86 Y202.995 E.2024
G2 X200.14 Y202.995 I-1.86 J.01 E.17345
G1 X200.14 Y209.79 E.2024
G1 X199.89 Y209.79 E.00745
G1 X199.89 Y210.79 E.02979
G1 X198.71 Y210.79 E.03515
G1 X198.71 Y202.997 E.23212
G2 X191.29 Y202.997 I-3.71 J.005 E.34685
G1 X191.29 Y210.79 E.23212
G1 X190.11 Y210.79 E.03515
G1 X190.11 Y209.79 E.02979
G1 X189.86 Y209.79 E.00745
G1 X189.86 Y202.995 E.2024
G2 X186.14 Y202.995 I-1.86 J.01 E.17345
G1 X186.14 Y209.79 E.2024
G1 X185.89 Y209.79 E.00745
G1 X185.89 Y210.79 E.02979
G1 X183.71 Y210.79 E.06494
G1 X183.71 Y191.21 E.58322
G1 X187.21 Y191.21 E.10425
G1 X187.21 Y169.21 E.65531
G1 X202.79 Y169.21 E.46408
G1 X202.79 Y191.15 E.65352
; WIPE_START
M204 S8000
G1 X203.79 Y191.167 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I-1.049 J.617 P1  F60000
G1 X204.92 Y193.091 Z1
G1 Z.6
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42234
G1 F14232.248
M204 S8000
G1 X204.579 Y192.749 E.01447
G1 X204.042 Y192.749 E.01608
G1 X204.751 Y193.458 E.03002
G1 X204.751 Y193.994 E.01608
G1 X203.506 Y192.749 E.05276
G1 X202.969 Y192.749 E.01608
G1 X204.751 Y194.531 E.07551
G1 X204.751 Y195.067 E.01608
G1 X202.433 Y192.749 E.09825
G1 X201.896 Y192.749 E.01608
G1 X204.751 Y195.604 E.12099
G1 X204.751 Y196.141 E.01608
G1 X188.749 Y180.139 E.67822
G1 X188.749 Y179.603 E.01608
G1 X201.251 Y192.104 E.52987
G1 X201.251 Y191.567 E.01608
G1 X188.749 Y179.066 E.52987
G1 X188.749 Y178.53 E.01608
G1 X201.251 Y191.031 E.52987
G1 X201.251 Y190.494 E.01608
G1 X188.749 Y177.993 E.52987
M73 P22 R12
G1 X188.749 Y177.457 E.01608
G1 X201.251 Y189.958 E.52987
G1 X201.251 Y189.421 E.01608
G1 X188.749 Y176.92 E.52987
G1 X188.749 Y176.383 E.01608
G1 X201.251 Y188.885 E.52987
G1 X201.251 Y188.348 E.01608
G1 X188.749 Y175.847 E.52987
G1 X188.749 Y175.31 E.01608
G1 X201.251 Y187.811 E.52987
G1 X201.251 Y187.275 E.01608
G1 X188.749 Y174.774 E.52987
G1 X188.749 Y174.237 E.01608
G1 X201.42 Y186.908 E.53706
; WIPE_START
G1 X200.713 Y186.201 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I1.216 J.058 P1  F60000
G1 X201.42 Y171.347 Z1
G1 Z.6
G1 E.4 F1800
G1 F14232.248
M204 S8000
G1 X200.823 Y170.749 E.02533
G1 X200.286 Y170.749 E.01608
G1 X201.251 Y171.714 E.04088
G1 X201.251 Y172.251 E.01608
G1 X199.749 Y170.749 E.06362
G1 X199.213 Y170.749 E.01608
G1 X201.251 Y172.787 E.08637
G1 X201.251 Y173.324 E.01608
G1 X198.676 Y170.749 E.10911
G1 X198.14 Y170.749 E.01608
G1 X201.251 Y173.86 E.13185
G1 X201.251 Y174.397 E.01608
G1 X197.603 Y170.749 E.1546
G1 X197.067 Y170.749 E.01608
G1 X201.251 Y174.933 E.17734
G1 X201.251 Y175.47 E.01608
G1 X196.53 Y170.749 E.20008
G1 X195.993 Y170.749 E.01608
G1 X201.251 Y176.007 E.22283
G1 X201.251 Y176.543 E.01608
G1 X198.575 Y173.868 E.11339
G3 X198.722 Y174.551 I-4.511 J1.322 E.02094
G1 X201.251 Y177.08 E.10719
G1 X201.251 Y177.616 E.01608
G1 X198.746 Y175.112 E.10615
G3 X198.699 Y175.601 I-2.474 J.007 E.01476
G1 X201.251 Y178.153 E.10816
G1 X201.251 Y178.689 E.01608
G1 X198.602 Y176.041 E.11228
G3 X198.464 Y176.439 I-2.059 J-.489 E.01266
G1 X201.251 Y179.226 E.11813
G1 X201.251 Y179.763 E.01608
G1 X198.289 Y176.801 E.12554
G1 X198.079 Y177.128 E.01164
G1 X201.251 Y180.299 E.13442
G1 X201.251 Y180.836 E.01608
G1 X197.849 Y177.434 E.14418
G3 X197.588 Y177.71 I-1.507 J-1.164 E.01139
G1 X201.251 Y181.372 E.15524
G1 X201.251 Y181.909 E.01608
G1 X197.3 Y177.958 E.16745
G3 X196.984 Y178.179 I-1.26 J-1.467 E.01157
G1 X201.251 Y182.446 E.18084
G1 X201.251 Y182.982 E.01608
G1 X196.639 Y178.37 E.19547
G3 X196.262 Y178.53 I-.986 J-1.805 E.01229
G1 X201.251 Y183.519 E.21145
G1 X201.251 Y184.055 E.01608
G1 X195.849 Y178.654 E.22895
G3 X195.387 Y178.728 I-1.239 J-6.181 E.01402
G1 X201.251 Y184.592 E.24853
G1 X201.251 Y185.128 E.01608
G1 X194.867 Y178.745 E.27058
G3 X194.26 Y178.674 I.155 J-3.989 E.01833
G1 X201.251 Y185.665 E.2963
G1 X201.251 Y186.202 E.01608
G1 X193.469 Y178.42 E.32984
G3 X191.577 Y176.528 I1.498 J-3.389 E.08203
G1 X188.749 Y173.701 E.11985
G1 X188.749 Y173.164 E.01608
G1 X191.322 Y175.736 E.10903
G3 X191.255 Y175.133 I2.985 J-.635 E.01822
G1 X188.749 Y172.627 E.1062
G1 X188.749 Y172.091 E.01608
G1 X191.269 Y174.611 E.10681
G3 X191.349 Y174.154 I2.324 J.169 E.01393
G1 X188.749 Y171.554 E.11018
G1 X188.749 Y171.018 E.01608
G1 X191.471 Y173.74 E.11537
G3 X191.63 Y173.362 I1.969 J.605 E.0123
G1 X189.018 Y170.749 E.11072
G1 X189.554 Y170.749 E.01608
G1 X191.826 Y173.021 E.09627
G3 X192.04 Y172.698 I1.352 J.666 E.01163
G1 X190.091 Y170.749 E.08261
G1 X190.628 Y170.749 E.01608
G1 X192.289 Y172.41 E.0704
G3 X192.564 Y172.15 I1.445 J1.253 E.0114
G1 X191.164 Y170.749 E.05935
G1 X191.701 Y170.749 E.01608
G1 X192.868 Y171.917 E.04947
G3 X193.2 Y171.712 I1.184 J1.551 E.01171
G1 X192.237 Y170.749 E.0408
G1 X192.774 Y170.749 E.01608
G1 X193.563 Y171.539 E.03345
G3 X193.961 Y171.4 I.894 J1.921 E.01265
G1 X193.311 Y170.749 E.02757
G1 X193.847 Y170.749 E.01608
G1 X194.399 Y171.301 E.02339
G3 X194.885 Y171.251 I.494 J2.406 E.01468
G1 X194.384 Y170.749 E.02126
G1 X194.92 Y170.749 E.01608
G1 X195.451 Y171.28 E.0225
G3 X196.136 Y171.429 I-.464 J3.793 E.02105
G1 X195.287 Y170.58 E.03599
; WIPE_START
G1 X195.994 Y171.287 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I-1.209 J.14 P1  F60000
G1 X199.599 Y202.387 Z1
G1 Z.6
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.106944
G1 F15000
M204 S8000
G1 X199.555 Y202.508 E.00065
; LINE_WIDTH: 0.13577
G1 X199.519 Y202.626 E.00091
; LINE_WIDTH: 0.173828
G1 X199.48 Y202.752 E.00136
; LINE_WIDTH: 0.199626
G1 X199.473 Y202.78 E.00036
; LINE_WIDTH: 0.226669
G1 X199.45 Y202.823 E.00071
; LINE_WIDTH: 0.281712
G2 X199.425 Y202.99 I.482 J.156 E.00319
G1 X199.425 Y209.194 E.11704
; WIPE_START
G1 X199.425 Y208.194 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I-.324 J1.173 P1  F60000
G1 X205.2 Y209.787 Z1
G1 Z.6
G1 E.4 F1800
; LINE_WIDTH: 0.21759
G1 F15000
M204 S8000
G1 X205.2 Y208.787 E.0138
; LINE_WIDTH: 0.239415
G1 X205.178 Y208.744 E.00076
; LINE_WIDTH: 0.283085
G1 X205.156 Y208.7 E.00093
; LINE_WIDTH: 0.326755
G1 X205.135 Y208.656 E.00109
; LINE_WIDTH: 0.370425
G1 X205.113 Y208.613 E.00126
; LINE_WIDTH: 0.411095
G1 F14666.937
G1 X205.094 Y208.594 E.00077
; LINE_WIDTH: 0.467502
G1 F12718.408
G1 X205.075 Y208.575 E.00089
G1 X205.075 Y202.96 E.18834
; LINE_WIDTH: 0.474802
G1 F12503.411
G2 X205.067 Y202.682 I-5.585 J.011 E.00947
; LINE_WIDTH: 0.515149
G1 F11435.141
G1 X205.017 Y202.144 E.02015
M204 S10000
G1 X204.86 Y201.377 F60000
; LINE_WIDTH: 0.105326
G1 F15000
M204 S8000
G2 X204.77 Y201.217 I-.265 J.045 E.00092
; WIPE_START
G1 X204.844 Y201.314 E-.24905
G1 X204.86 Y201.377 E-.13095
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I1.217 J.016 P1  F60000
G1 X204.92 Y196.847 Z1
G1 Z.6
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42234
G1 F14232.248
M204 S8000
G1 X188.749 Y180.676 E.68541
G1 X188.749 Y181.213 E.01608
G1 X204.751 Y197.214 E.67822
G1 X204.751 Y197.75 E.01608
G1 X188.749 Y181.749 E.67822
G1 X188.749 Y182.286 E.01608
G1 X204.751 Y198.287 E.67822
G1 X204.751 Y198.823 E.01608
G1 X188.749 Y182.822 E.67822
G1 X188.749 Y183.359 E.01608
G1 X204.751 Y199.36 E.67822
G1 X204.751 Y199.897 E.01608
G1 X188.749 Y183.896 E.67822
G1 X188.749 Y184.432 E.01608
G1 X204.751 Y200.433 E.67822
G1 X204.751 Y200.81 E.0113
G1 X204.661 Y200.88 E.00341
G1 X188.749 Y184.969 E.67442
G1 X188.749 Y185.505 E.01608
G1 X202.998 Y199.754 E.60394
G2 X202.332 Y199.625 I-.75 J2.084 E.02041
G1 X188.749 Y186.042 E.57572
G1 X188.749 Y186.578 E.01608
G1 X201.778 Y199.607 E.55223
G1 X201.312 Y199.678 E.01412
G1 X188.749 Y187.115 E.5325
G1 X188.749 Y187.652 E.01608
G1 X200.886 Y199.788 E.5144
G2 X200.511 Y199.95 I.485 J1.635 E.01226
G1 X188.749 Y188.188 E.49853
G1 X188.749 Y188.725 E.01608
G1 X200.162 Y200.138 E.48374
G2 X199.852 Y200.364 I5.408 J7.724 E.01151
G1 X188.749 Y189.261 E.4706
G1 X188.749 Y189.798 E.01608
G1 X197.172 Y198.221 E.35702
G2 X196.357 Y197.942 I-2.309 J5.418 E.02586
G1 X188.749 Y190.335 E.32245
G1 X188.749 Y190.871 E.01608
G1 X195.678 Y197.8 E.29368
G2 X195.093 Y197.752 I-.687 J4.764 E.0176
G1 X188.749 Y191.408 E.2689
G1 X188.749 Y191.944 E.01608
G1 X194.583 Y197.778 E.24726
G2 X194.102 Y197.834 I-.015 J1.968 E.01454
G1 X188.749 Y192.481 E.22688
G1 X188.749 Y192.749 E.00805
G1 X188.481 Y192.749 E.00803
G1 X193.658 Y197.926 E.21941
G2 X193.251 Y198.056 I.662 J2.775 E.01281
G1 X187.945 Y192.749 E.22491
G1 X187.408 Y192.749 E.01608
G1 X192.864 Y198.205 E.23123
G2 X192.507 Y198.385 I1.024 J2.467 E.01198
G1 X186.872 Y192.749 E.23887
G1 X186.335 Y192.749 E.01608
G1 X192.166 Y198.581 E.24717
G2 X191.853 Y198.804 I1.341 J2.213 E.01154
G1 X185.799 Y192.749 E.25663
G1 X185.262 Y192.749 E.01608
G1 X191.553 Y199.041 E.26667
G2 X191.285 Y199.309 I1.187 J1.457 E.01139
G1 X185.249 Y193.274 E.25582
G1 X185.249 Y193.81 E.01608
G1 X191.02 Y199.581 E.2446
G2 X190.784 Y199.881 I1.094 J1.104 E.01148
G1 X185.249 Y194.347 E.23459
M73 P22 R11
G1 X185.249 Y194.883 E.01608
G1 X190.563 Y200.197 E.22521
G2 X190.369 Y200.539 I2.196 J1.467 E.01181
G1 X185.249 Y195.42 E.217
G1 X185.249 Y195.956 E.01608
G1 X189.063 Y199.77 E.16166
G2 X188.38 Y199.624 I-.932 J2.674 E.021
G1 X185.249 Y196.493 E.1327
G1 X185.249 Y197.03 E.01608
G1 X187.827 Y199.608 E.10927
G2 X187.349 Y199.666 I.148 J3.21 E.01446
G1 X185.249 Y197.566 E.089
G1 X185.249 Y198.103 E.01608
G1 X186.921 Y199.774 E.07085
G2 X186.543 Y199.933 I1.656 J4.485 E.01229
G1 X185.249 Y198.639 E.05482
G1 X185.249 Y199.176 E.01608
G1 X186.194 Y200.12 E.04004
G2 X185.878 Y200.341 I4.216 J6.367 E.01155
G1 X185.249 Y199.712 E.02665
G1 X185.249 Y200.249 E.01608
G1 X185.717 Y200.717 E.01982
M204 S10000
G1 X185.244 Y201.198 F60000
; FEATURE: Gap infill
; LINE_WIDTH: 0.106467
G1 F15000
M204 S8000
G1 X185.193 Y201.261 E.00041
G2 X185.14 Y201.376 I.118 J.124 E.00065
M204 S10000
G1 X185.249 Y202.189 F60000
; LINE_WIDTH: 0.510781
G1 F11541.899
M204 S8000
G1 X184.954 Y202.396 E.01332
G2 X184.932 Y202.704 I6.153 J.605 E.0114
; LINE_WIDTH: 0.467879
G1 F12707.109
G1 X184.925 Y208.575 E.19708
; LINE_WIDTH: 0.448765
G1 F13305.572
G1 X184.906 Y208.594 E.00085
; LINE_WIDTH: 0.411095
G1 F14666.937
G1 X184.887 Y208.613 E.00077
; LINE_WIDTH: 0.370428
G1 F15000
G1 X184.866 Y208.656 E.00126
; LINE_WIDTH: 0.326763
G1 X184.844 Y208.7 E.00109
; LINE_WIDTH: 0.283098
G1 X184.822 Y208.744 E.00093
; LINE_WIDTH: 0.218607
G1 X184.8 Y208.787 E.00068
G1 X184.8 Y209.787 E.01388
; WIPE_START
G1 X184.8 Y208.787 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I-.086 J1.214 P1  F60000
G1 X190.575 Y209.194 Z1
G1 Z.6
G1 E.4 F1800
; LINE_WIDTH: 0.282602
G1 F15000
M204 S8000
G3 X190.575 Y202.987 I464.032 J-3.102 E.11753
G1 X190.569 Y202.632 E.00672
; LINE_WIDTH: 0.34489
G1 X190.566 Y202.487 E.00344
; LINE_WIDTH: 0.388143
G1 X190.558 Y202.343 E.00394
; LINE_WIDTH: 0.413693
G1 F14564.182
G1 X190.557 Y202.335 E.00023
; OBJECT_ID: 12
; COOLING_NODE: 0
; WIPE_START
G1 X190.558 Y202.343 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 16
M625
; start printing object, unique label id: 12
M624 AgAAAAAAAAA=
M204 S10000
G17
G3 Z1 I1.213 J.1 P1  F60000
G1 X197.536 Y117.28 Z1
G1 Z.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X197.481 Y117.356 E.00302
G3 X194.745 Y111.593 I-2.473 J-2.357 E.42553
G1 X194.933 Y111.584 E.00605
G3 X197.828 Y116.928 I.076 J3.415 E.24092
G1 X197.575 Y117.234 E.01277
; COOLING_NODE: 0
M204 S10000
G1 X197.221 Y117.024 F60000
M73 P23 R11
G1 F13265.217
M204 S8000
G1 X197.186 Y117.073 E.00193
G3 X194.775 Y111.999 I-2.18 J-2.074 E.37495
G1 X194.938 Y111.991 E.00523
G3 X197.49 Y116.697 I.068 J3.008 E.21221
G1 X197.259 Y116.978 E.01166
; COOLING_NODE: 0
M204 S10000
G1 X196.906 Y116.769 F60000
G1 F13265.217
M204 S8000
G1 X196.891 Y116.789 E.00083
G3 X194.806 Y112.405 I-1.888 J-1.79 E.32437
G1 X194.943 Y112.398 E.00441
G3 X197.151 Y116.467 I.061 J2.601 E.18351
G1 X196.944 Y116.722 E.01057
; COOLING_NODE: 0
M204 S250
G1 X196.605 Y116.518 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X196.285 Y116.787 E.01246
G3 X194.835 Y112.796 I-1.284 J-1.792 E.24219
G1 X194.948 Y112.791 E.00336
G3 X196.636 Y116.473 I.053 J2.204 E.15302
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X196.285 Y116.787 E-.17885
G1 X195.909 Y117.015 E-.16702
G1 X195.824 Y117.043 E-.03414
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I-1.108 J.502 P1  F60000
G1 X202.79 Y132.416 Z1
G1 Z.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X205.084 Y132.416 E.07376
G1 X205.084 Y141.924 E.30573
G1 X204.882 Y141.959 E.00659
G2 X199.853 Y140.809 I-2.889 J1.061 E.19672
G1 X199.551 Y141.135 E.0143
G2 X190.446 Y141.143 I-4.551 J1.873 E.37388
G2 X185.118 Y141.959 I-2.441 J1.862 E.2115
G1 X184.916 Y141.924 E.00659
G1 X184.916 Y132.416 E.30573
G1 X188.416 Y132.416 E.11255
G1 X188.416 Y110.416 E.70744
G1 X201.584 Y110.416 E.42342
G1 X201.584 Y132.416 E.70744
G1 X202.73 Y132.416 E.03686
; COOLING_NODE: 0
M204 S10000
G1 X202.79 Y132.009 F60000
G1 F13265.217
M204 S8000
G1 X205.491 Y132.009 E.08685
G1 X205.491 Y149.991 E.57823
G1 X204.909 Y149.991 E.01871
G1 X204.909 Y148.991 E.03216
G1 X204.459 Y148.991 E.01447
G1 X204.459 Y144.011 E.16012
G2 X199.664 Y141.726 I-2.46 J-1.011 E.25929
G1 X199.45 Y142.171 E.01588
G2 X196.855 Y138.89 I-4.576 J.952 E.13948
G2 X190.691 Y141.671 I-1.848 J4.126 E.24565
G1 X190.55 Y142.171 E.01671
G2 X189.213 Y140.632 I-2.744 J1.035 E.06695
G2 X185.541 Y144.008 I-1.202 J2.378 E.20754
G1 X185.541 Y148.991 E.16025
G1 X185.091 Y148.991 E.01447
G1 X185.091 Y149.991 E.03216
G1 X184.509 Y149.991 E.01871
G1 X184.509 Y132.009 E.57823
G1 X188.009 Y132.009 E.11255
G1 X188.009 Y110.009 E.70744
G1 X201.991 Y110.009 E.4496
G1 X201.991 Y132.009 E.70744
G1 X202.73 Y132.009 E.02377
; COOLING_NODE: 0
M204 S10000
G1 X202.79 Y131.602 F60000
G1 F13265.217
M204 S8000
G1 X205.898 Y131.602 E.09994
G1 X205.898 Y150.398 E.60441
G1 X204.502 Y150.398 E.04489
G1 X204.502 Y149.398 E.03216
G1 X204.052 Y149.398 E.01447
G1 X204.052 Y143.924 E.17601
G2 X199.948 Y143.927 I-2.053 J-.924 E.28868
G1 X199.948 Y149.398 E.17593
G1 X199.498 Y149.398 E.01447
G1 X199.498 Y150.398 E.03216
G1 X199.102 Y150.398 E.01273
G1 X199.102 Y142.992 E.23814
G2 X190.898 Y142.992 I-4.102 J.01 E.41374
G1 X190.898 Y150.398 E.23814
G1 X190.502 Y150.398 E.01273
G1 X190.502 Y149.398 E.03216
G1 X190.052 Y149.398 E.01447
G1 X190.052 Y143.924 E.17601
G2 X185.948 Y143.927 I-2.053 J-.924 E.28868
G1 X185.948 Y149.398 E.17593
G1 X185.498 Y149.398 E.01447
G1 X185.498 Y150.398 E.03216
G1 X184.102 Y150.398 E.04489
G1 X184.102 Y131.602 E.60441
G1 X187.602 Y131.602 E.11255
G1 X187.602 Y109.602 E.70744
G1 X202.398 Y109.602 E.47578
G1 X202.398 Y131.602 E.70744
G1 X202.73 Y131.602 E.01068
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y131.21 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X206.29 Y131.21 E.10425
G1 X206.29 Y150.79 E.58322
G1 X204.11 Y150.79 E.06494
G1 X204.11 Y149.79 E.02979
G1 X203.66 Y149.79 E.0134
G1 X203.66 Y143.835 E.17737
G2 X200.34 Y143.836 I-1.66 J-.833 E.22529
G1 X200.34 Y149.79 E.17734
G1 X199.89 Y149.79 E.0134
G1 X199.89 Y150.79 E.02979
G1 X198.71 Y150.79 E.03515
G1 X198.71 Y142.997 E.23212
G2 X191.29 Y142.997 I-3.71 J.005 E.34685
G1 X191.29 Y150.79 E.23212
G1 X190.11 Y150.79 E.03515
G1 X190.11 Y149.79 E.02979
G1 X189.66 Y149.79 E.0134
G1 X189.66 Y143.835 E.17737
G2 X186.34 Y143.836 I-1.66 J-.831 E.22511
G1 X186.34 Y149.79 E.17734
G1 X185.89 Y149.79 E.0134
G1 X185.89 Y150.79 E.02979
G1 X183.71 Y150.79 E.06494
G1 X183.71 Y131.21 E.58322
G1 X187.21 Y131.21 E.10425
G1 X187.21 Y109.21 E.65531
G1 X202.79 Y109.21 E.46408
G1 X202.79 Y131.15 E.65352
; WIPE_START
M204 S8000
G1 X203.79 Y131.167 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I-1.049 J.617 P1  F60000
G1 X204.92 Y133.09 Z1
G1 Z.6
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42232
G1 F14232.998
M204 S8000
G1 X204.58 Y132.749 E.01442
G1 X204.043 Y132.749 E.01608
G1 X204.751 Y133.457 E.02997
G1 X204.751 Y133.993 E.01608
G1 X203.507 Y132.749 E.05271
G1 X202.97 Y132.749 E.01608
G1 X204.751 Y134.53 E.07545
G1 X204.751 Y135.066 E.01608
G1 X202.434 Y132.749 E.0982
G1 X201.897 Y132.749 E.01608
G1 X204.751 Y135.603 E.12094
G1 X204.751 Y136.139 E.01608
G1 X188.749 Y120.138 E.67819
G1 X188.749 Y119.602 E.01608
G1 X201.251 Y132.103 E.52984
G1 X201.251 Y131.566 E.01608
G1 X188.749 Y119.065 E.52984
G1 X188.749 Y118.529 E.01608
G1 X201.251 Y131.03 E.52984
G1 X201.251 Y130.493 E.01608
G1 X188.749 Y117.992 E.52984
G1 X188.749 Y117.456 E.01608
G1 X201.251 Y129.957 E.52984
G1 X201.251 Y129.42 E.01608
G1 X188.749 Y116.919 E.52984
G1 X188.749 Y116.382 E.01608
G1 X201.251 Y128.884 E.52984
G1 X201.251 Y128.347 E.01608
G1 X188.749 Y115.846 E.52984
G1 X188.749 Y115.309 E.01608
G1 X201.251 Y127.81 E.52984
G1 X201.251 Y127.274 E.01608
G1 X188.749 Y114.773 E.52984
G1 X188.749 Y114.236 E.01608
G1 X201.42 Y126.907 E.53704
; WIPE_START
G1 X200.713 Y126.2 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I1.216 J.058 P1  F60000
G1 X201.42 Y111.347 Z1
G1 Z.6
G1 E.4 F1800
G1 F14232.998
M204 S8000
G1 X200.823 Y110.749 E.02533
G1 X200.286 Y110.749 E.01608
G1 X201.251 Y111.714 E.04087
G1 X201.251 Y112.25 E.01608
G1 X199.75 Y110.749 E.06362
G1 X199.213 Y110.749 E.01608
G1 X201.251 Y112.787 E.08636
G1 X201.251 Y113.324 E.01608
G1 X198.676 Y110.749 E.1091
G1 X198.14 Y110.749 E.01608
G1 X201.251 Y113.86 E.13184
G1 X201.251 Y114.397 E.01608
G1 X197.603 Y110.749 E.15458
G1 X197.067 Y110.749 E.01608
G1 X201.251 Y114.933 E.17732
G1 X201.251 Y115.47 E.01608
G1 X196.53 Y110.749 E.20006
G1 X195.994 Y110.749 E.01608
G1 X201.251 Y116.006 E.2228
G1 X201.251 Y116.543 E.01608
G1 X198.575 Y113.868 E.11339
G3 X198.722 Y114.55 I-4.502 J1.321 E.02095
G1 X201.251 Y117.079 E.10719
G1 X201.251 Y117.616 E.01608
G1 X198.746 Y115.111 E.10615
G3 X198.699 Y115.601 I-2.473 J.008 E.01475
G1 X201.251 Y118.152 E.10815
G1 X201.251 Y118.689 E.01608
G1 X198.602 Y116.04 E.11227
G3 X198.464 Y116.439 I-2.056 J-.488 E.01266
G1 X201.251 Y119.226 E.11811
G1 X201.251 Y119.762 E.01608
G1 X198.29 Y116.802 E.12547
G3 X198.085 Y117.133 I-1.344 J-.604 E.01171
G1 X201.251 Y120.299 E.13418
G1 X201.251 Y120.835 E.01608
G1 X197.845 Y117.429 E.14436
G3 X197.588 Y117.71 I-1.302 J-.932 E.01141
G1 X201.251 Y121.372 E.15521
G1 X201.251 Y121.908 E.01608
G1 X197.3 Y117.958 E.16743
G3 X196.984 Y118.179 I-1.262 J-1.469 E.01157
G1 X201.251 Y122.445 E.18081
G1 X201.251 Y122.981 E.01608
G1 X196.639 Y118.37 E.19544
G3 X196.262 Y118.53 I-.986 J-1.805 E.01229
G1 X201.251 Y123.518 E.21142
G1 X201.251 Y124.055 E.01608
G1 X195.849 Y118.653 E.22892
G3 X195.388 Y118.728 I-1.244 J-6.207 E.01402
G1 X201.251 Y124.591 E.24848
G1 X201.251 Y125.128 E.01608
G1 X194.868 Y118.745 E.27053
G3 X194.261 Y118.675 I.155 J-3.995 E.01832
G1 X201.251 Y125.664 E.29624
M73 P24 R11
G1 X201.251 Y126.201 E.01608
G1 X193.47 Y118.421 E.32976
G3 X191.576 Y116.526 I1.488 J-3.382 E.08215
G1 X188.749 Y113.7 E.11981
G1 X188.749 Y113.163 E.01608
G1 X191.322 Y115.735 E.10901
G3 X191.255 Y115.132 I2.983 J-.635 E.01822
G1 X188.749 Y112.627 E.10619
G1 X188.749 Y112.09 E.01608
G1 X191.27 Y114.61 E.10681
G3 X191.349 Y114.153 I2.32 J.169 E.01392
G1 X188.749 Y111.553 E.11018
G1 X188.749 Y111.017 E.01608
G1 X191.472 Y113.739 E.11537
G3 X191.634 Y113.365 I1.525 J.441 E.01225
G1 X189.019 Y110.749 E.11086
G1 X189.555 Y110.749 E.01608
G1 X191.819 Y113.014 E.09596
G3 X192.04 Y112.698 I1.688 J.946 E.01157
G1 X190.092 Y110.749 E.08259
G1 X190.628 Y110.749 E.01608
G1 X192.289 Y112.41 E.07039
G3 X192.565 Y112.149 I1.441 J1.249 E.01139
G1 X191.165 Y110.749 E.05934
G1 X191.701 Y110.749 E.01608
G1 X192.868 Y111.916 E.04946
G3 X193.2 Y111.712 I1.188 J1.559 E.01171
G1 X192.238 Y110.749 E.04079
G1 X192.774 Y110.749 E.01608
G1 X193.564 Y111.539 E.03344
G3 X193.961 Y111.4 I.894 J1.922 E.01265
G1 X193.311 Y110.749 E.02756
G1 X193.848 Y110.749 E.01608
G1 X194.404 Y111.306 E.0236
G3 X194.894 Y111.259 I.407 J1.659 E.01479
G1 X194.384 Y110.749 E.02161
G1 X194.921 Y110.749 E.01608
G1 X195.451 Y111.28 E.0225
G3 X196.137 Y111.429 I-.464 J3.789 E.02105
G1 X195.288 Y110.58 E.036
; WIPE_START
G1 X195.995 Y111.287 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I-1.209 J.14 P1  F60000
G1 X199.6 Y142.385 Z1
G1 Z.6
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.105833
G1 F15000
M204 S8000
G1 X199.56 Y142.495 E.00058
; LINE_WIDTH: 0.133629
G1 X199.518 Y142.625 E.00098
; LINE_WIDTH: 0.174956
G1 X199.478 Y142.76 E.00146
; LINE_WIDTH: 0.201812
G1 X199.473 Y142.779 E.00026
; LINE_WIDTH: 0.226999
G1 X199.45 Y142.822 E.00071
; LINE_WIDTH: 0.281994
G2 X199.425 Y142.99 I.519 J.162 E.00322
G1 X199.427 Y143.142 E.00287
; LINE_WIDTH: 0.297508
G1 X199.439 Y143.39 E.005
; LINE_WIDTH: 0.334785
G1 X199.464 Y143.635 E.00566
; LINE_WIDTH: 0.361103
G1 X199.466 Y143.651 E.0004
; LINE_WIDTH: 0.381307
G1 X199.484 Y143.772 E.00328
; LINE_WIDTH: 0.420604
G1 F14297.683
G1 X199.505 Y143.912 E.00422
; LINE_WIDTH: 0.481346
G1 F12316.809
G1 X199.525 Y144.011 E.00349
G1 X199.525 Y149.194 E.17952
; WIPE_START
G1 X199.525 Y148.194 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I-.132 J1.21 P1  F60000
G1 X204.975 Y148.787 Z1
G1 Z.6
G1 E.4 F1800
; LINE_WIDTH: 0.667448
G1 F8646.535
M204 S8000
G1 X204.985 Y144.051 E.23366
; LINE_WIDTH: 0.626373
G1 F9255.252
G1 X205.006 Y143.916 E.0063
; LINE_WIDTH: 0.581962
G1 F10017.787
G1 X205.029 Y143.755 E.00694
; LINE_WIDTH: 0.544759
G1 F10760.43
G1 X205.044 Y143.612 E.00568
; LINE_WIDTH: 0.514207
G1 F11458.005
G1 X205.059 Y143.447 E.00618
; LINE_WIDTH: 0.477007
G1 F12439.917
G2 X205.067 Y142.673 I-6.984 J-.454 E.02657
; LINE_WIDTH: 0.510863
G1 F11539.878
G1 X205.045 Y142.384 E.01071
G1 X204.753 Y142.189 E.01298
M204 S10000
G1 X204.86 Y141.377 F60000
; LINE_WIDTH: 0.104927
G1 F15000
M204 S8000
G2 X204.77 Y141.217 I-.287 J.057 E.00091
; WIPE_START
G1 X204.844 Y141.314 E-.24842
G1 X204.86 Y141.377 E-.13158
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I1.217 J.016 P1  F60000
G1 X204.92 Y136.846 Z1
G1 Z.6
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42232
G1 F14232.998
M204 S8000
G1 X188.749 Y120.675 E.68538
G1 X188.749 Y121.211 E.01608
G1 X204.751 Y137.212 E.67819
G1 X204.751 Y137.749 E.01608
G1 X188.749 Y121.748 E.67819
G1 X188.749 Y122.285 E.01608
G1 X204.751 Y138.286 E.67819
G1 X204.751 Y138.822 E.01608
G1 X188.749 Y122.821 E.67819
G1 X188.749 Y123.358 E.01608
G1 X204.751 Y139.359 E.67819
G1 X204.751 Y139.895 E.01608
G1 X188.749 Y123.894 E.67819
G1 X188.749 Y124.431 E.01608
G1 X204.751 Y140.432 E.67819
G1 X204.751 Y140.807 E.01123
G1 X204.66 Y140.878 E.00345
G1 X188.749 Y124.967 E.67436
G1 X188.749 Y125.504 E.01608
G1 X202.996 Y139.751 E.60384
G1 X202.418 Y139.624 E.01773
G1 X202.329 Y139.62 E.00269
G1 X188.749 Y126.04 E.57555
G1 X188.749 Y126.577 E.01608
G1 X201.782 Y139.609 E.55237
G2 X201.308 Y139.672 I.077 J2.399 E.01435
G1 X188.749 Y127.114 E.53228
G1 X188.749 Y127.65 E.01608
G1 X200.887 Y139.787 E.51442
G2 X200.509 Y139.946 I.607 J1.967 E.0123
G1 X188.749 Y128.187 E.49843
G1 X188.749 Y128.723 E.01608
G1 X200.166 Y140.14 E.48389
G2 X199.859 Y140.369 I.752 J1.331 E.01152
G1 X188.749 Y129.26 E.47085
G1 X188.749 Y129.796 E.01608
G1 X197.176 Y138.222 E.35714
G2 X196.359 Y137.943 I-2.298 J5.373 E.02589
G1 X188.749 Y130.333 E.32253
G1 X188.749 Y130.869 E.01608
G1 X195.68 Y137.8 E.29375
G2 X195.095 Y137.752 I-.695 J4.836 E.0176
G1 X188.749 Y131.406 E.26895
G1 X188.749 Y131.942 E.01608
G1 X194.585 Y137.778 E.24732
G2 X194.104 Y137.833 I-.016 J1.968 E.01455
G1 X188.749 Y132.479 E.22694
G1 X188.749 Y132.749 E.00811
G1 X188.483 Y132.749 E.00798
G1 X193.659 Y137.925 E.21938
G2 X193.253 Y138.055 I.66 J2.773 E.01281
G1 X187.947 Y132.749 E.22488
G1 X187.41 Y132.749 E.01608
G1 X192.865 Y138.204 E.2312
G2 X192.509 Y138.384 I1.021 J2.463 E.01198
G1 X186.874 Y132.749 E.23883
G1 X186.337 Y132.749 E.01608
G1 X192.168 Y138.58 E.24712
G2 X191.854 Y138.803 I1.335 J2.207 E.01154
G1 X185.801 Y132.749 E.25658
G1 X185.264 Y132.749 E.01608
G1 X191.554 Y139.04 E.26661
G2 X191.286 Y139.308 I1.19 J1.46 E.01139
G1 X185.249 Y133.271 E.25585
G1 X185.249 Y133.808 E.01608
G1 X191.021 Y139.58 E.24464
G2 X190.785 Y139.88 I1.093 J1.104 E.01148
G1 X185.249 Y134.345 E.23461
G1 X185.249 Y134.881 E.01608
G1 X190.564 Y140.195 E.22523
G2 X190.37 Y140.538 I2.194 J1.467 E.01181
G1 X185.249 Y135.418 E.21702
G1 X185.249 Y135.954 E.01608
G1 X189.071 Y139.776 E.16197
G1 X188.925 Y139.727 E.00463
G1 X188.38 Y139.622 E.01661
G1 X185.249 Y136.491 E.13269
G1 X185.249 Y137.027 E.01608
G1 X187.834 Y139.612 E.10955
G2 X187.35 Y139.665 I-.03 J1.973 E.01463
G1 X185.249 Y137.564 E.08904
G1 X185.249 Y138.1 E.01608
G1 X186.923 Y139.774 E.07092
G2 X186.544 Y139.931 I1.792 J4.85 E.01231
G1 X185.249 Y138.637 E.05485
G1 X185.249 Y139.174 E.01608
G1 X186.196 Y140.12 E.04011
G2 X185.88 Y140.34 I3.883 J5.912 E.01155
G1 X185.249 Y139.71 E.02671
G1 X185.249 Y140.247 E.01608
G1 X185.718 Y140.716 E.01987
M204 S10000
G1 X185.244 Y141.197 F60000
; FEATURE: Gap infill
; LINE_WIDTH: 0.106452
G1 F15000
M204 S8000
G1 X185.184 Y141.273 E.00049
G2 X185.14 Y141.377 I.11 J.107 E.00058
M204 S10000
G1 X185.247 Y142.189 F60000
; LINE_WIDTH: 0.509824
G1 F11565.559
M204 S8000
G1 X184.954 Y142.394 E.01319
G2 X184.932 Y142.696 I6.454 J.628 E.01119
; LINE_WIDTH: 0.47753
G1 F12424.941
G1 X184.926 Y143.149 E.01554
G2 X184.942 Y143.47 I25.752 J-1.126 E.01102
; LINE_WIDTH: 0.51638
G1 F11405.407
G1 X184.956 Y143.612 E.00536
; LINE_WIDTH: 0.54744
G1 F10703.244
G1 X184.974 Y143.781 E.00675
; LINE_WIDTH: 0.586593
G1 F9932.453
G1 X184.995 Y143.922 E.00613
; LINE_WIDTH: 0.628971
G1 F9214.219
G1 X185.016 Y144.063 E.0066
; LINE_WIDTH: 0.667489
G1 F8645.969
G1 X185.025 Y148.787 E.2331
; WIPE_START
G1 X185.023 Y147.787 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I-.304 J1.178 P1  F60000
G1 X190.475 Y149.194 Z1
G1 Z.6
G1 E.4 F1800
; LINE_WIDTH: 0.481262
G1 F12319.157
M204 S8000
G1 X190.475 Y144.013 E.17942
G1 X190.496 Y143.901 E.00393
; LINE_WIDTH: 0.419166
G1 F14352.334
G1 X190.516 Y143.773 E.00385
; LINE_WIDTH: 0.383012
G1 F15000
G1 X190.533 Y143.661 E.00305
; LINE_WIDTH: 0.349497
G1 X190.549 Y143.516 E.00352
; LINE_WIDTH: 0.305289
G1 X190.574 Y143.132 E.00798
; LINE_WIDTH: 0.282393
G1 X190.575 Y142.875 E.00486
G3 X190.597 Y142.837 I.033 J-.006 E.00091
; LINE_WIDTH: 0.222897
G1 X190.62 Y142.81 E.00049
; LINE_WIDTH: 0.179777
G1 X190.642 Y142.784 E.00037
; LINE_WIDTH: 0.151674
G1 X190.65 Y142.758 E.00024
; LINE_WIDTH: 0.119163
G1 X190.705 Y142.463 E.00181
; OBJECT_ID: 8
; COOLING_NODE: 0
; WIPE_START
G1 X190.65 Y142.758 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 12
M625
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z1 I.591 J-1.064 P1  F60000
G1 X141.874 Y115.684 Z1
G1 Z.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X141.874 Y174.884 E1.90366
G1 X140.126 Y174.884 E.05623
G1 X140.126 Y115.684 E1.90366
G1 X121.406 Y115.684 E.60195
G1 X121.406 Y113.516 E.0697
G1 X157.584 Y113.516 E1.16334
G1 X157.584 Y115.684 E.0697
G1 X155.874 Y115.684 E.05497
G1 X155.874 Y174.884 E1.90366
G1 X154.126 Y174.884 E.05624
G1 X154.126 Y115.684 E1.90366
G1 X141.934 Y115.684 E.39203
; COOLING_NODE: 0
M204 S10000
G1 X142.281 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X142.281 Y175.291 E1.90366
G1 X141.376 Y175.291 E.02911
G1 X141.376 Y185.678 E.33403
G1 X141 Y186.05 E.01701
G1 X140.624 Y185.678 E.01701
G1 X140.624 Y175.291 E.33403
G1 X139.719 Y175.291 E.02911
G1 X139.719 Y116.091 E1.90366
G1 X120.999 Y116.091 E.60195
G1 X120.999 Y113.109 E.09588
G1 X157.991 Y113.109 E1.18952
G1 X157.991 Y116.091 E.09588
G1 X156.281 Y116.091 E.05497
G1 X156.281 Y175.291 E1.90366
M73 P25 R11
G1 X155.376 Y175.291 E.02911
G1 X155.376 Y185.678 E.33403
G1 X155 Y186.05 E.01701
G1 X154.624 Y185.678 E.01701
G1 X154.624 Y175.291 E.33403
G1 X153.719 Y175.291 E.02911
G1 X153.719 Y116.091 E1.90366
G1 X142.341 Y116.091 E.36585
; COOLING_NODE: 0
M204 S10000
G1 X142.689 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X142.689 Y174.902 E1.87806
G1 X143.29 Y174.902 E.01935
G1 X143.29 Y175.698 E.02559
G1 X141.783 Y175.698 E.04846
G1 X141.783 Y185.849 E.32641
G1 X141.479 Y186.149 E.01374
G1 X141.479 Y187.018 E.02794
G3 X141.139 Y187.298 I-4.87 J-5.569 E.01419
G1 X140.861 Y187.298 E.00893
G3 X140.521 Y187.018 I4.53 J-5.849 E.01419
G1 X140.521 Y186.149 E.02794
G1 X140.217 Y185.849 E.01374
G1 X140.217 Y175.698 E.32641
G1 X138.71 Y175.698 E.04846
G1 X138.71 Y174.902 E.02559
G1 X139.311 Y174.902 E.01935
G1 X139.311 Y116.498 E1.87806
G1 X120.592 Y116.498 E.60195
G1 X120.592 Y112.702 E.12206
G1 X158.398 Y112.702 E1.2157
G1 X158.398 Y116.498 E.12206
G1 X156.689 Y116.498 E.05497
G1 X156.689 Y174.902 E1.87806
G1 X157.29 Y174.902 E.01934
G1 X157.29 Y175.698 E.02559
G1 X155.783 Y175.698 E.04846
G1 X155.783 Y185.849 E.32641
G1 X155.479 Y186.149 E.01374
G1 X155.479 Y186.518 E.01186
G3 X155.139 Y186.798 I-4.918 J-5.627 E.01419
G1 X154.861 Y186.798 E.00893
G3 X154.521 Y186.518 I4.808 J-6.183 E.01418
G1 X154.521 Y186.149 E.01186
G1 X154.217 Y185.849 E.01374
G1 X154.217 Y175.698 E.32641
G1 X152.71 Y175.698 E.04846
G1 X152.71 Y174.902 E.02559
G1 X153.311 Y174.902 E.01935
G1 X153.311 Y116.498 E1.87806
G1 X142.749 Y116.498 E.33967
; COOLING_NODE: 0
M204 S250
G1 X143.081 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F3693
M204 S5000
G1 X143.081 Y174.51 E1.7163
G1 X143.682 Y174.51 E.01792
G1 X143.682 Y176.09 E.04706
G1 X142.175 Y176.09 E.04488
G1 X142.175 Y186.012 E.29555
G1 X141.871 Y186.313 E.01272
G1 X141.871 Y187.201 E.02648
G3 X141.274 Y187.69 I-8.501 J-9.788 E.02299
G1 X140.726 Y187.69 E.01632
G3 X140.129 Y187.201 I7.904 J-10.278 E.02299
G1 X140.129 Y186.313 E.02648
G1 X139.825 Y186.012 E.01272
G1 X139.825 Y176.09 E.29555
G1 X138.318 Y176.09 E.04488
G1 X138.318 Y174.51 E.04706
G1 X138.919 Y174.51 E.01792
G1 X138.919 Y116.89 E1.7163
G1 X120.2 Y116.89 E.55759
G1 X120.2 Y112.31 E.13642
G1 X158.79 Y112.31 E1.14947
G1 X158.79 Y116.89 E.13642
G1 X157.081 Y116.89 E.05092
G1 X157.081 Y174.51 E1.7163
G1 X157.682 Y174.51 E.01792
G1 X157.682 Y176.09 E.04706
G1 X156.175 Y176.09 E.04488
G1 X156.175 Y186.012 E.29555
G1 X155.871 Y186.313 E.01272
G1 X155.871 Y186.701 E.01159
G3 X155.274 Y187.19 I-8.488 J-9.773 E.02299
G1 X154.725 Y187.19 E.01634
G3 X154.129 Y186.701 I8.502 J-10.996 E.02298
G1 X154.129 Y186.313 E.01159
G1 X153.825 Y186.012 E.01272
G1 X153.825 Y176.09 E.29555
G1 X152.318 Y176.09 E.04488
G1 X152.318 Y174.51 E.04706
G1 X152.919 Y174.51 E.01792
G1 X152.919 Y116.89 E1.7163
G1 X143.141 Y116.89 E.29128
; WIPE_START
G1 F12000
M204 S8000
M73 P26 R11
G1 X143.14 Y117.89 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I-1.216 J-.045 P1  F60000
G1 X141 Y175.087 Z1
G1 Z.6
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.38824
G1 F15000
M204 S8000
G1 X141 Y185.764 E.29123
; WIPE_START
G1 X141 Y184.764 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I-.131 J1.21 P1  F60000
G1 X154.724 Y186.25 Z1
G1 Z.6
G1 E.4 F1800
; LINE_WIDTH: 0.291203
G1 F15000
M204 S8000
G1 X154.915 Y186.423 E.00504
G2 X155.022 Y186.465 I.085 J-.061 E.00238
G2 X155.276 Y186.25 I-.556 J-.917 E.00655
M204 S10000
G1 X155 Y185.764 F60000
; LINE_WIDTH: 0.38824
G1 F15000
M204 S8000
G1 X155 Y175.087 E.29123
; WIPE_START
G1 X155 Y176.087 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I1.217 J0 P1  F60000
G1 X155 Y174.009 Z1
G1 Z.6
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.63052
G1 F9189.925
M204 S8000
G1 X155 Y115.54 E2.71391
; WIPE_START
G1 X155 Y116.54 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I-1.182 J-.288 P1  F60000
G1 X141 Y174.009 Z1
G1 Z.6
G1 E.4 F1800
; LINE_WIDTH: 0.6305
G1 F9190.239
M204 S8000
G1 X141 Y115.54 E2.71382
; WIPE_START
G1 X141 Y116.54 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I-1.217 J-.01 P1  F60000
G1 X140.518 Y174.492 Z1
G1 Z.6
G1 E.4 F1800
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X141.482 Y174.492 E.02873
G1 X141.482 Y115.48 E1.75771
G1 X141.545 Y115.34 E.00459
G1 X141.671 Y115.292 E.004
G1 X154.329 Y115.292 E.37704
G1 X154.494 Y115.388 E.00568
G1 X154.518 Y115.48 E.00284
G1 X154.518 Y174.492 E1.75771
G1 X155.482 Y174.492 E.02873
G1 X155.482 Y115.48 E1.75771
G1 X155.545 Y115.34 E.00459
G1 X155.671 Y115.292 E.004
G1 X157.192 Y115.292 E.0453
G1 X157.192 Y113.908 E.04121
G1 X121.798 Y113.908 E1.05423
G1 X121.798 Y115.292 E.04121
G1 X140.329 Y115.292 E.55196
G1 X140.494 Y115.388 E.00568
G1 X140.518 Y115.48 E.00284
G1 X140.518 Y174.432 E1.75592
; WIPE_START
G1 X140.518 Y173.432 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I1.217 J.01 P1  F60000
G1 X141 Y115.48 Z1
G1 Z.6
G1 E.4 F1800
; LINE_WIDTH: 0.609449
G1 F9531.728
M204 S8000
G1 X141.059 Y115.396 E.00461
; LINE_WIDTH: 0.567347
G1 F10296.953
G1 X141.118 Y115.311 E.00426
; LINE_WIDTH: 0.525245
G1 F11195.771
G1 X141.177 Y115.227 E.00392
; LINE_WIDTH: 0.483143
G1 F12266.51
G1 X141.236 Y115.143 E.00358
; LINE_WIDTH: 0.441041
G1 F13563.715
G1 X141.294 Y115.058 E.00324
; LINE_WIDTH: 0.442124
G1 F13526.941
G1 X141.384 Y114.991 E.00351
; LINE_WIDTH: 0.48639
G1 F12176.697
G1 X141.473 Y114.925 E.0039
; LINE_WIDTH: 0.546015
G1 F10733.568
G3 X141.671 Y114.852 I.154 J.113 E.0089
G1 X154.329 Y114.852 E.50305
; LINE_WIDTH: 0.525099
G1 F11199.176
G1 X154.455 Y114.92 E.00545
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X154.58 Y114.989 E.00498
; LINE_WIDTH: 0.441012
G1 F13564.713
G1 X154.706 Y115.058 E.0045
; LINE_WIDTH: 0.441043
G1 F13563.647
G1 X154.764 Y115.143 E.00324
; LINE_WIDTH: 0.483149
G1 F12266.343
G1 X154.823 Y115.227 E.00358
; LINE_WIDTH: 0.525255
G1 F11195.538
G1 X154.882 Y115.311 E.00392
; LINE_WIDTH: 0.567361
G1 F10296.678
G1 X154.941 Y115.396 E.00426
; LINE_WIDTH: 0.609467
G1 F9531.425
G1 X155 Y115.48 E.00461
G1 X155.059 Y115.396 E.00461
; LINE_WIDTH: 0.567361
G1 F10296.678
G1 X155.118 Y115.311 E.00426
; LINE_WIDTH: 0.525255
G1 F11195.538
G1 X155.177 Y115.227 E.00392
; LINE_WIDTH: 0.483149
G1 F12266.343
G1 X155.236 Y115.143 E.00358
; LINE_WIDTH: 0.441043
G1 F13563.647
G1 X155.294 Y115.058 E.00324
; LINE_WIDTH: 0.442124
G1 F13526.941
G1 X155.384 Y114.991 E.00351
; LINE_WIDTH: 0.48639
G1 F12176.697
G1 X155.473 Y114.925 E.0039
; LINE_WIDTH: 0.546608
G1 F10720.923
G1 X155.562 Y114.858 E.00443
G3 X156.752 Y114.852 I1.064 J90.624 E.04735
G1 X156.752 Y114.348 E.02002
G1 X155.671 Y114.348 E.043
; LINE_WIDTH: 0.525099
G1 F11199.176
G1 X155.447 Y114.327 E.00856
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X155.224 Y114.306 E.00781
; LINE_WIDTH: 0.441012
G1 F13564.713
G1 X155 Y114.285 E.00706
G1 X154.776 Y114.306 E.00706
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X154.553 Y114.327 E.00781
; LINE_WIDTH: 0.545754
G1 F10739.142
G1 X154.329 Y114.348 E.00892
G1 X141.671 Y114.348 E.50279
; LINE_WIDTH: 0.525099
G1 F11199.176
G1 X141.447 Y114.327 E.00855
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X141.224 Y114.306 E.00781
; LINE_WIDTH: 0.441012
G1 F13564.713
G1 X141 Y114.285 E.00706
G1 X140.776 Y114.306 E.00706
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X140.553 Y114.327 E.00781
; LINE_WIDTH: 0.545992
G1 F10734.049
G1 X140.329 Y114.348 E.00893
G1 X122.238 Y114.348 E.71891
G1 X122.238 Y114.852 E.02
G1 X140.329 Y114.852 E.71891
; LINE_WIDTH: 0.525099
G1 F11199.176
G1 X140.455 Y114.92 E.00545
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X140.58 Y114.989 E.00498
; LINE_WIDTH: 0.441012
G1 F13564.713
G1 X140.706 Y115.058 E.0045
; LINE_WIDTH: 0.441041
G1 F13563.715
G1 X140.758 Y115.133 E.00286
; LINE_WIDTH: 0.483143
G1 F12266.51
G1 X140.81 Y115.207 E.00316
; LINE_WIDTH: 0.525245
G1 F11195.771
G1 X140.862 Y115.282 E.00347
; LINE_WIDTH: 0.567347
G1 F10296.953
G1 X140.914 Y115.356 E.00377
; LINE_WIDTH: 0.609449
G1 F9531.728
G1 X140.966 Y115.431 E.00407
M204 S10000
G1 X141.032 Y114.673 F60000
; LINE_WIDTH: 0.5508
G1 F10632.434
M204 S8000
G2 X141.033 Y114.78 I-.026 J.054 E.00985
; WIPE_START
G1 X140.968 Y114.783 E-.09701
G1 X140.937 Y114.728 E-.09433
G1 X140.968 Y114.673 E-.09433
G1 X141.032 Y114.673 E-.09432
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I0 J1.217 P1  F60000
G1 X155.032 Y114.673 Z1
G1 Z.6
G1 E.4 F1800
; LINE_WIDTH: 0.55082
G1 F10632.014
M204 S8000
G2 X155.033 Y114.78 I-.026 J.054 E.00985
; COOLING_NODE: 0
; WIPE_START
G1 X154.968 Y114.783 E-.09701
G1 X154.937 Y114.728 E-.09433
G1 X154.968 Y114.673 E-.09433
G1 X155.032 Y114.673 E-.09432
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I-.03 J-1.217 P1  F60000
G1 X114.594 Y115.684 Z1
G1 Z.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X112.416 Y115.684 E.07003
G1 X112.416 Y113.516 E.0697
G1 X114.594 Y113.516 E.07003
G1 X114.594 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X115.001 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X112.009 Y116.091 E.09621
G1 X112.009 Y113.109 E.09588
G1 X115.001 Y113.109 E.09621
G1 X115.001 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X115.408 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X111.602 Y116.498 E.12239
G1 X111.602 Y112.702 E.12206
G1 X115.408 Y112.702 E.12239
G1 X115.408 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X115.8 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F3693
M204 S5000
G1 X111.21 Y116.89 E.13672
G1 X111.21 Y112.31 E.13642
G1 X115.8 Y112.31 E.13672
G1 X115.8 Y116.83 E.13464
; WIPE_START
G1 F12000
M204 S8000
G1 X114.8 Y116.843 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1 I1.135 J-.438 P1  F60000
G1 X114.202 Y115.292 Z1
G1 Z.6
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X114.202 Y113.908 E.04121
G1 X112.808 Y113.908 E.04151
G1 X112.808 Y115.292 E.04121
G1 X114.142 Y115.292 E.03972
M204 S10000
G1 X113.762 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X113.762 Y114.348 E.02
G1 X113.248 Y114.348 E.0204
G1 X113.248 Y114.852 E.02
G1 X113.702 Y114.852 E.01802
; CHANGE_LAYER
; Z_HEIGHT: 0.8
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F10731.32
G1 X113.248 Y114.852 E-.17225
G1 X113.248 Y114.348 E-.19122
G1 X113.292 Y114.348 E-.01654
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 4/27
; update layer progress
M73 L4
M991 S0 P3 ;notify layer change
M106 S51
; OBJECT_ID: 16
; COOLING_NODE: 0
; start printing object, unique label id: 16
M624 BAAAAAAAAAA=
M204 S10000
G17
G3 Z1 I-.751 J.958 P1  F60000
G1 X195.027 Y178.408 Z1
G1 Z.8
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X194.745 Y178.402 E.00907
G3 X194.575 Y171.609 I.255 J-3.405 E.32307
G1 X194.915 Y171.583 E.01097
G3 X195.255 Y178.402 I.085 J3.414 E.33951
G1 X195.087 Y178.406 E.00541
; COOLING_NODE: 0
M204 S10000
G1 X195.026 Y178.001 F60000
G1 F13265.217
M204 S8000
G1 X194.775 Y177.997 E.00805
G3 X194.625 Y172.013 I.225 J-2.999 E.28456
G1 X194.925 Y171.991 E.00966
G3 X195.225 Y177.997 I.075 J3.007 E.29904
G1 X195.086 Y178 E.00447
; COOLING_NODE: 0
M204 S10000
G1 X195.024 Y177.595 F60000
G1 F13265.217
M204 S8000
G1 X194.806 Y177.592 E.00704
G3 X194.676 Y172.417 I.194 J-2.594 E.24605
G1 X194.935 Y172.398 E.00835
G3 X195.194 Y177.592 I.065 J2.6 E.25857
G1 X195.084 Y177.594 E.00353
; COOLING_NODE: 0
M204 S250
G1 X195.024 Y177.204 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X194.835 Y177.201 E.00563
G3 X194.725 Y172.807 I.165 J-2.203 E.19357
G1 X194.945 Y172.79 E.00657
G3 X195.165 Y177.201 I.055 J2.208 E.20341
G1 X195.084 Y177.203 E.00241
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X194.835 Y177.201 E-.09461
G1 X194.401 Y177.128 E-.16714
G1 X194.112 Y177.014 E-.11825
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-1.1 J.52 P1  F60000
G1 X200.541 Y190.62 Z1.2
G1 Z.8
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X189.38 Y190.62 E.35888
G1 X189.38 Y188.38 E.07203
G1 X188.416 Y188.38 E.03101
G1 X188.416 Y170.416 E.57763
G1 X201.584 Y170.416 E.42342
G1 X201.584 Y188.38 E.57763
G1 X200.62 Y188.38 E.03101
G1 X200.62 Y190.62 E.07203
G1 X200.601 Y190.62 E.00061
; COOLING_NODE: 0
M204 S10000
G1 X201.017 Y191.027 F60000
G1 F13265.217
M204 S8000
G1 X188.973 Y191.027 E.38729
G1 X188.973 Y188.787 E.07203
G1 X188.009 Y188.787 E.03101
G1 X188.009 Y170.009 E.60381
G1 X201.991 Y170.009 E.4496
G1 X201.991 Y188.787 E.60381
G1 X201.027 Y188.787 E.03101
G1 X201.027 Y190.976 E.07041
; COOLING_NODE: 0
M204 S10000
G1 X201.434 Y191.21 F60000
G1 F13265.217
M204 S8000
G1 X201.434 Y191.434 E.00719
G1 X188.566 Y191.434 E.41377
G1 X188.566 Y189.194 E.07203
G1 X187.602 Y189.194 E.03101
G1 X187.602 Y169.602 E.62999
G1 X202.398 Y169.602 E.47578
G1 X202.398 Y189.194 E.62999
G1 X201.434 Y189.194 E.03101
G1 X201.434 Y191.15 E.06291
; COOLING_NODE: 1
; WIPE_START
G1 X201.434 Y191.434 E-.10782
G1 X200.717 Y191.434 E-.27218
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I.131 J1.21 P1  F60000
G1 X202.79 Y191.21 Z1.2
G1 Z.8
M73 P27 R11
G1 E.4 F1800
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X206.29 Y191.21 E.10425
G1 X206.29 Y210.79 E.58322
; object ids of layer 4 start: 8,12,16
M624 BwAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer4 end: 8,12,16
M625
G1 X204.11 Y210.79 E.06494
G1 X204.11 Y209.79 E.02979
G1 X203.86 Y209.79 E.00745
G1 X203.86 Y202.995 E.2024
G2 X200.14 Y202.995 I-1.86 J.014 E.17324
G1 X200.14 Y209.79 E.20241
G1 X199.89 Y209.79 E.00745
G1 X199.89 Y210.79 E.02979
G1 X198.71 Y210.79 E.03515
G1 X198.71 Y202.997 E.23212
G2 X191.29 Y202.997 I-3.71 J.004 E.34694
G1 X191.29 Y210.79 E.23212
G1 X190.11 Y210.79 E.03515
G1 X190.11 Y209.79 E.02979
G1 X189.86 Y209.79 E.00745
G1 X189.86 Y202.995 E.2024
G2 X186.14 Y202.995 I-1.86 J.014 E.17324
G1 X186.14 Y209.79 E.20241
G1 X185.89 Y209.79 E.00745
G1 X185.89 Y210.79 E.02979
G1 X183.71 Y210.79 E.06494
G1 X183.71 Y191.21 E.58322
G1 X187.21 Y191.21 E.10425
G1 X187.21 Y169.21 E.65531
G1 X202.79 Y169.21 E.46408
G1 X202.79 Y191.15 E.65352
; WIPE_START
M204 S8000
G1 X203.79 Y191.167 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I.208 J-1.199 P1  F60000
G1 X199.685 Y190.456 Z1.2
G1 Z.8
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42437
G1 F14156.507
M204 S8000
G1 X200.286 Y189.854 E.02565
G1 X200.286 Y189.315 E.01625
G1 X199.315 Y190.286 E.0414
G1 X198.775 Y190.286 E.01625
G1 X200.456 Y188.606 E.07162
M204 S10000
G1 X200.846 Y188.216 F60000
G1 F14156.507
M204 S8000
G1 X201.251 Y187.811 E.01725
G1 X201.251 Y187.272 E.01625
G1 X198.236 Y190.286 E.12847
G1 X197.696 Y190.286 E.01625
G1 X201.251 Y186.732 E.15145
G1 X201.251 Y186.193 E.01625
G1 X197.157 Y190.286 E.17444
G1 X196.618 Y190.286 E.01625
G1 X201.251 Y185.653 E.19743
G1 X201.251 Y185.114 E.01625
G1 X196.078 Y190.286 E.22042
G1 X195.539 Y190.286 E.01625
G1 X201.251 Y184.574 E.2434
G1 X201.251 Y184.035 E.01625
G1 X194.999 Y190.286 E.26639
G1 X194.46 Y190.286 E.01625
G1 X201.251 Y183.496 E.28938
G1 X201.251 Y182.956 E.01625
G1 X193.92 Y190.286 E.31237
G1 X193.381 Y190.286 E.01625
G1 X201.251 Y182.417 E.33535
G1 X201.251 Y181.877 E.01625
G1 X192.841 Y190.286 E.35834
G1 X192.302 Y190.286 E.01625
G1 X201.251 Y181.338 E.38133
G1 X201.251 Y180.798 E.01625
G1 X191.762 Y190.286 E.40432
G1 X191.223 Y190.286 E.01625
G1 X201.251 Y180.259 E.4273
G1 X201.251 Y179.719 E.01625
G1 X190.684 Y190.286 E.45029
G1 X190.144 Y190.286 E.01625
G1 X201.251 Y179.18 E.47328
G1 X201.251 Y178.64 E.01625
G1 X189.714 Y190.178 E.49163
G1 X189.714 Y189.638 E.01625
G1 X201.251 Y178.101 E.49163
G1 X201.251 Y177.562 E.01625
G1 X189.714 Y189.099 E.49163
G1 X189.714 Y188.559 E.01625
G1 X201.251 Y177.022 E.49163
G1 X201.251 Y176.483 E.01625
G1 X189.687 Y188.046 E.49276
G1 X189.148 Y188.046 E.01625
G1 X201.251 Y175.943 E.51575
G1 X201.251 Y175.404 E.01625
G1 X188.749 Y187.905 E.53271
G1 X188.749 Y187.366 E.01625
G1 X201.251 Y174.864 E.53271
G1 X201.251 Y174.325 E.01625
G1 X188.749 Y186.826 E.53271
G1 X188.749 Y186.287 E.01625
G1 X196.694 Y178.342 E.33854
G3 X195.841 Y178.656 I-1.908 J-3.874 E.02744
G1 X188.749 Y185.747 E.30219
G1 X188.749 Y185.208 E.01625
G1 X195.218 Y178.739 E.27564
G3 X194.681 Y178.736 I-.244 J-4.316 E.01617
G1 X188.749 Y184.668 E.25278
G1 X188.749 Y184.129 E.01625
G1 X194.214 Y178.664 E.23288
G3 X193.792 Y178.547 I.374 J-2.17 E.01323
G1 X188.749 Y183.589 E.21488
G1 X188.749 Y183.05 E.01625
G1 X193.407 Y178.392 E.19849
G3 X193.057 Y178.203 I.772 J-1.848 E.01201
G1 X188.749 Y182.511 E.18357
G1 X188.749 Y181.971 E.01625
G1 X192.734 Y177.986 E.16982
G3 X192.442 Y177.739 I1.085 J-1.587 E.01156
G1 X188.749 Y181.432 E.15733
G1 X188.749 Y180.892 E.01625
G1 X192.176 Y177.465 E.14603
G3 X191.938 Y177.164 I1.391 J-1.34 E.01159
G1 X188.749 Y180.353 E.1359
G1 X188.749 Y179.813 E.01625
G1 X191.731 Y176.832 E.12704
G3 X191.55 Y176.473 I1.706 J-1.079 E.01213
G1 X188.749 Y179.274 E.11936
G1 X188.749 Y178.734 E.01625
G1 X191.408 Y176.076 E.11327
G3 X191.307 Y175.637 I2.141 J-.722 E.01359
G1 X188.749 Y178.195 E.10898
G1 X188.749 Y177.655 E.01625
G1 X191.256 Y175.149 E.10681
G3 X191.272 Y174.593 I4.672 J-.141 E.01676
G1 X188.749 Y177.116 E.1075
G1 X188.749 Y176.577 E.01625
G1 X191.709 Y173.617 E.12613
; WIPE_START
G1 X191.002 Y174.324 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I1.114 J-.491 P1  F60000
G1 X189.352 Y170.58 Z1.2
G1 Z.8
G1 E.4 F1800
G1 F14156.507
M204 S8000
G1 X188.749 Y171.182 E.02567
G1 X188.749 Y171.721 E.01625
G1 X189.721 Y170.749 E.04143
G1 X190.261 Y170.749 E.01625
G1 X188.749 Y172.261 E.06441
G1 X188.749 Y172.8 E.01625
G1 X190.8 Y170.749 E.0874
G1 X191.34 Y170.749 E.01625
G1 X188.749 Y173.34 E.11039
G1 X188.749 Y173.879 E.01625
G1 X191.879 Y170.749 E.13338
G1 X192.419 Y170.749 E.01625
G1 X188.749 Y174.419 E.15636
G1 X188.749 Y174.958 E.01625
G1 X192.958 Y170.749 E.17935
G1 X193.498 Y170.749 E.01625
G1 X188.749 Y175.498 E.20234
G1 X188.749 Y176.037 E.01625
G1 X194.037 Y170.749 E.22533
G1 X194.577 Y170.749 E.01625
G1 X193.912 Y171.414 E.02831
G3 X194.592 Y171.273 I1.193 J4.057 E.02094
G1 X195.116 Y170.749 E.02232
G1 X195.655 Y170.749 E.01625
G1 X195.149 Y171.256 E.02158
G3 X195.64 Y171.304 I.004 J2.478 E.01489
G1 X196.195 Y170.749 E.02364
G1 X196.734 Y170.749 E.01625
G1 X196.075 Y171.409 E.02809
G3 X196.47 Y171.553 I-.522 J2.044 E.0127
G1 X197.274 Y170.749 E.03424
G1 X197.813 Y170.749 E.01625
G1 X196.83 Y171.732 E.04189
G3 X197.162 Y171.94 I-.869 J1.759 E.01182
G1 X198.353 Y170.749 E.05073
G1 X198.892 Y170.749 E.01625
G1 X197.464 Y172.177 E.06085
G3 X197.738 Y172.443 I-1.189 J1.504 E.01151
G1 X199.432 Y170.749 E.07215
G1 X199.971 Y170.749 E.01625
G1 X197.985 Y172.735 E.08463
G3 X198.203 Y173.056 I-1.492 J1.249 E.01172
G1 X200.511 Y170.749 E.09831
G1 X201.05 Y170.749 E.01625
G1 X198.392 Y173.407 E.11327
G3 X198.547 Y173.791 I-1.837 J.968 E.0125
G1 X201.251 Y171.088 E.11519
G1 X201.251 Y171.628 E.01625
G1 X198.666 Y174.212 E.11014
G3 X198.736 Y174.682 I-5.536 J1.062 E.01431
G1 X201.251 Y172.167 E.10717
G1 X201.251 Y172.707 E.01625
G1 X198.741 Y175.216 E.10695
G3 X198.651 Y175.845 I-3.896 J-.234 E.01917
G1 X201.251 Y173.246 E.11077
G1 X201.251 Y173.785 E.01625
G1 X197.775 Y177.262 E.14813
; WIPE_START
G1 X198.482 Y176.554 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-1.216 J.044 P1  F60000
G1 X199.683 Y210.114 Z1.2
G1 Z.8
G1 E.4 F1800
; FEATURE: Top surface
; LINE_WIDTH: 0.42
G1 F12000
M204 S2000
G1 X199.214 Y210.583 E.01975
G1 X199.08 Y210.716
G1 X198.784 Y210.479
G1 X198.917 Y210.346
G1 X199.933 Y209.331 E.04277
G1 X200.066 Y209.197
G1 X200.066 Y208.664
G1 X199.933 Y208.797
G1 X198.917 Y209.813 E.04277
G1 X198.784 Y209.946
G1 X198.784 Y209.413
G1 X198.917 Y209.279
G1 X199.933 Y208.264 E.04277
G1 X200.066 Y208.13
G1 X200.066 Y207.597
G1 X199.933 Y207.731
G1 X198.917 Y208.746 E.04277
G1 X198.784 Y208.88
G1 X198.784 Y208.346
G1 X198.917 Y208.213
G1 X199.933 Y207.197 E.04277
G1 X200.066 Y207.064
G1 X200.066 Y206.531
G1 X199.933 Y206.664
G1 X198.917 Y207.679 E.04277
G1 X198.784 Y207.813
G1 X198.784 Y207.28
G1 X198.917 Y207.146
G1 X199.933 Y206.131 E.04277
G1 X200.066 Y205.997
G1 X200.066 Y205.464
G1 X199.933 Y205.598
G1 X198.917 Y206.613 E.04277
G1 X198.784 Y206.747
G1 X198.784 Y206.213
G1 X198.917 Y206.08
G1 X199.933 Y205.064 E.04277
G1 X200.066 Y204.931
G1 X200.066 Y204.398
G1 X199.933 Y204.531
G1 X198.917 Y205.546 E.04277
G1 X198.784 Y205.68
G1 X198.784 Y205.147
G1 X198.917 Y205.013
G1 X199.933 Y203.998 E.04277
G1 X200.066 Y203.864
G1 X200.066 Y203.331
G1 X199.933 Y203.465
G1 X198.917 Y204.48 E.04277
G1 X198.784 Y204.614
G1 X198.784 Y204.08
G1 X198.917 Y203.947
G1 X199.936 Y202.928 E.0429
G1 X200.069 Y202.795
G1 X200.204 Y202.127
G1 X200.07 Y202.26
G1 X198.917 Y203.413 E.04857
; WIPE_START
M204 S8000
G1 X199.624 Y202.706 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-.804 J-.913 P1  F60000
G1 X190.682 Y210.583 Z1.2
G1 Z.8
G1 E.4 F1800
G1 F12000
M204 S2000
G1 X191.083 Y210.182 E.01689
G1 X191.216 Y210.048
G1 X191.216 Y209.515
G1 X191.083 Y209.648
G1 X190.317 Y210.414 E.03224
G1 X190.184 Y210.547
G1 X190.184 Y210.014
G1 X190.317 Y209.88
G1 X191.083 Y209.115 E.03224
G1 X191.216 Y208.982
G1 X191.216 Y208.448
G1 X191.083 Y208.582
G1 X190.082 Y209.583 E.04215
G1 X189.948 Y209.716
G1 X189.934 Y209.198
G1 X190.067 Y209.064
G1 X191.083 Y208.049 E.04277
G1 X191.216 Y207.915
G1 X191.216 Y207.382
G1 X191.083 Y207.515
G1 X190.067 Y208.531 E.04277
G1 X189.934 Y208.664
G1 X189.934 Y208.131
G1 X190.067 Y207.997
G1 X191.083 Y206.982 E.04277
G1 X191.216 Y206.848
G1 X191.216 Y206.315
G1 X191.083 Y206.449
G1 X190.067 Y207.464 E.04277
G1 X189.934 Y207.598
G1 X189.934 Y207.065
G1 X190.067 Y206.931
G1 X191.083 Y205.916 E.04277
G1 X191.216 Y205.782
G1 X191.216 Y205.249
G1 X191.083 Y205.382
G1 X190.067 Y206.398 E.04277
G1 X189.934 Y206.531
G1 X189.934 Y205.998
G1 X190.067 Y205.864
G1 X191.083 Y204.849 E.04277
G1 X191.216 Y204.715
G1 X191.216 Y204.182
M73 P28 R11
G1 X191.083 Y204.316
G1 X190.067 Y205.331 E.04277
G1 X189.934 Y205.465
G1 X189.934 Y204.931
G1 X190.067 Y204.798
G1 X191.083 Y203.783 E.04277
G1 X191.216 Y203.649
G1 X191.216 Y203.116
G1 X191.083 Y203.249
G1 X190.067 Y204.265 E.04277
G1 X189.934 Y204.398
G1 X189.934 Y203.865
G1 X190.067 Y203.731
G1 X191.095 Y202.704 E.04328
G1 X191.229 Y202.57
G1 X191.329 Y201.937
G1 X191.195 Y202.07
G1 X190.067 Y203.198 E.04751
G1 X189.934 Y203.332
G1 X189.908 Y202.824
G1 X190.042 Y202.69
G1 X191.511 Y201.221 E.06188
; WIPE_START
M204 S8000
G1 X190.804 Y201.928 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-1.017 J-.669 P1  F60000
G1 X185.683 Y209.716 Z1.2
G1 Z.8
G1 E.4 F1800
G1 F12000
M204 S2000
G1 X184.816 Y210.583 E.03651
G1 X184.682 Y210.716
G1 X184.149 Y210.716
G1 X184.283 Y210.583
G1 X185.933 Y208.933 E.06951
G1 X186.066 Y208.799
G1 X186.066 Y208.266
G1 X185.933 Y208.399
G1 X183.917 Y210.415 E.08489
G1 X183.784 Y210.548
G1 X183.784 Y210.015
G1 X183.917 Y209.881
G1 X185.933 Y207.866 E.08489
G1 X186.066 Y207.732
G1 X186.066 Y207.199
G1 X185.933 Y207.333
G1 X183.917 Y209.348 E.08489
G1 X183.784 Y209.482
G1 X183.784 Y208.948
G1 X183.917 Y208.815
G1 X185.933 Y206.8 E.08489
G1 X186.066 Y206.666
G1 X186.066 Y206.133
G1 X185.933 Y206.266
G1 X183.917 Y208.282 E.08489
G1 X183.784 Y208.415
G1 X183.784 Y207.882
G1 X183.917 Y207.748
G1 X185.933 Y205.733 E.08489
G1 X186.066 Y205.599
G1 X186.066 Y205.066
G1 X185.933 Y205.2
G1 X183.917 Y207.215 E.08489
G1 X183.784 Y207.349
G1 X183.784 Y206.815
G1 X183.917 Y206.682
G1 X185.933 Y204.667 E.08489
G1 X186.066 Y204.533
G1 X186.066 Y204
G1 X185.933 Y204.133
G1 X183.917 Y206.148 E.08489
G1 X183.784 Y206.282
G1 X183.784 Y205.749
G1 X183.917 Y205.615
G1 X185.933 Y203.6 E.08489
G1 X186.066 Y203.466
G1 X186.066 Y202.933
G1 X185.933 Y203.067
G1 X183.917 Y205.082 E.08489
G1 X183.784 Y205.216
G1 X183.784 Y204.682
G1 X183.917 Y204.549
G1 X186.005 Y202.461 E.08793
; WIPE_START
M204 S8000
G1 X185.298 Y203.168 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-.417 J1.143 P1  F60000
G1 X205.613 Y210.583 Z1.2
G1 Z.8
G1 E.4 F1800
G1 F12000
M204 S2000
G1 X206.083 Y210.113 E.01979
G1 X206.216 Y209.979
G1 X206.216 Y209.446
G1 X206.083 Y209.58
G1 X205.08 Y210.583 E.04225
G1 X204.946 Y210.716
G1 X204.413 Y210.716
G1 X204.546 Y210.583
G1 X206.083 Y209.046 E.06471
G1 X206.216 Y208.913
G1 X206.216 Y208.379
G1 X206.083 Y208.513
G1 X204.317 Y210.278 E.07436
G1 X204.184 Y210.412
G1 X204.184 Y209.879
G1 X204.317 Y209.745
G1 X206.083 Y207.98 E.07436
G1 X206.216 Y207.846
G1 X206.216 Y207.313
G1 X206.083 Y207.447
G1 X204.067 Y209.462 E.08489
G1 X203.934 Y209.595
G1 X203.934 Y209.062
G1 X204.067 Y208.929
G1 X206.083 Y206.913 E.08489
G1 X206.216 Y206.78
G1 X206.216 Y206.246
G1 X206.083 Y206.38
G1 X204.067 Y208.395 E.08489
G1 X203.934 Y208.529
G1 X203.934 Y207.996
G1 X204.067 Y207.862
G1 X206.083 Y205.847 E.08489
G1 X206.216 Y205.713
G1 X206.216 Y205.18
G1 X206.083 Y205.314
G1 X204.067 Y207.329 E.08489
G1 X203.934 Y207.462
G1 X203.934 Y206.929
G1 X204.067 Y206.796
G1 X206.083 Y204.78 E.08489
G1 X206.216 Y204.647
G1 X206.216 Y204.113
G1 X206.083 Y204.247
G1 X204.067 Y206.262 E.08489
G1 X203.934 Y206.396
G1 X203.934 Y205.863
G1 X204.067 Y205.729
G1 X206.083 Y203.714 E.08489
G1 X206.216 Y203.58
G1 X206.216 Y203.047
G1 X206.083 Y203.181
G1 X204.067 Y205.196 E.08489
G1 X203.934 Y205.329
G1 X203.934 Y204.796
G1 X204.067 Y204.663
G1 X206.083 Y202.647 E.08489
G1 X206.216 Y202.514
G1 X206.216 Y201.98
G1 X206.083 Y202.114
G1 X204.067 Y204.129 E.08489
G1 X203.934 Y204.263
G1 X203.934 Y203.73
G1 X204.067 Y203.596
G1 X206.083 Y201.581 E.08489
G1 X206.216 Y201.447
G1 X206.216 Y200.914
G1 X206.083 Y201.048
G1 X204.067 Y203.063 E.08489
G1 X203.934 Y203.196
G1 X203.889 Y202.708
G1 X204.023 Y202.574
G1 X206.083 Y200.514 E.08677
G1 X206.216 Y200.381
G1 X206.216 Y199.847
G1 X206.083 Y199.981
G1 X203.893 Y202.171 E.09224
G1 X203.759 Y202.304
G1 X203.568 Y201.963
G1 X203.701 Y201.829
G1 X206.083 Y199.448 E.10031
G1 X206.216 Y199.314
G1 X206.216 Y198.781
G1 X206.083 Y198.914
G1 X203.46 Y201.537 E.11048
G1 X203.326 Y201.671
G1 X203.034 Y201.43
G1 X203.168 Y201.296
G1 X206.083 Y198.381 E.12278
G1 X206.216 Y198.248
G1 X206.216 Y197.714
G1 X206.083 Y197.848
G1 X202.825 Y201.105 E.13721
G1 X202.692 Y201.239
G1 X202.287 Y201.11
G1 X202.421 Y200.977
G1 X206.083 Y197.315 E.15426
G1 X206.216 Y197.181
G1 X206.216 Y196.648
G1 X206.083 Y196.781
G1 X201.928 Y200.936 E.175
G1 X201.795 Y201.069
G1 X201.125 Y201.206
G1 X201.259 Y201.072
G1 X206.083 Y196.248 E.20321
G1 X206.216 Y196.115
G1 X206.216 Y195.581
G1 X206.083 Y195.715
G1 X198.915 Y202.883 E.30195
G1 X198.781 Y203.017
G1 X198.736 Y202.528
G1 X198.87 Y202.394
G1 X206.083 Y195.182 E.30383
G1 X206.216 Y195.048
G1 X206.216 Y194.515
G1 X206.083 Y194.648
G1 X198.775 Y201.956 E.30784
G1 X198.641 Y202.09
G1 X198.507 Y201.691
G1 X198.641 Y201.557
G1 X206.083 Y194.115 E.31348
G1 X206.216 Y193.982
G1 X206.216 Y193.448
G1 X206.083 Y193.582
G1 X198.474 Y201.191 E.32053
G1 X198.34 Y201.325
G1 X198.143 Y200.988
G1 X198.277 Y200.855
G1 X206.083 Y193.049 E.32883
G1 X206.216 Y192.915
G1 X206.216 Y192.382
G1 X206.083 Y192.515
G1 X198.052 Y200.546 E.3383
G1 X197.918 Y200.68
G1 X197.668 Y200.397
G1 X197.801 Y200.263
G1 X206.083 Y191.982 E.34884
G1 X206.216 Y191.848
G1 X206.216 Y191.315
G1 X206.083 Y191.449
G1 X197.525 Y200.006 E.36048
G1 X197.391 Y200.14
G1 X197.089 Y199.909
G1 X197.222 Y199.776
G1 X205.581 Y191.417 E.35209
G1 X205.714 Y191.284
G1 X205.181 Y191.284
G1 X205.048 Y191.417
G1 X196.893 Y199.572 E.3435
G1 X196.76 Y199.705
G1 X196.401 Y199.531
G1 X196.535 Y199.397
G1 X204.514 Y191.417 E.33614
G1 X204.648 Y191.284
G1 X204.115 Y191.284
G1 X203.981 Y191.417
G1 X196.144 Y199.254 E.33013
G1 X196.01 Y199.388
G1 X195.582 Y199.283
G1 X195.716 Y199.149
G1 X203.448 Y191.417 E.3257
G1 X203.581 Y191.284
G1 X203.048 Y191.284
G1 X202.915 Y191.417
G1 X195.241 Y199.091 E.32324
G1 X195.107 Y199.225
G1 X194.571 Y199.227
G1 X194.705 Y199.094
G1 X202.583 Y191.216 E.33184
G1 X202.716 Y191.082
G1 X202.716 Y190.549
G1 X202.583 Y190.683
G1 X201.656 Y191.609 E.03902
G1 X201.523 Y191.743
G1 X201.523 Y191.21
G1 X201.656 Y191.076
G1 X202.583 Y190.15 E.03902
G1 X202.716 Y190.016
G1 X202.716 Y189.483
G1 X202.583 Y189.616
G1 X201.656 Y190.543 E.03902
G1 X201.523 Y190.676
G1 X201.523 Y190.143
G1 X201.656 Y190.009
G1 X202.25 Y189.416 E.02499
; WIPE_START
M204 S8000
G1 X201.656 Y190.009 E-.31883
G1 X201.542 Y190.123 E-.06118
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-1.216 J.053 P1  F60000
G1 X201.609 Y191.656 Z1.2
G1 Z.8
G1 E.4 F1800
G1 F12000
M204 S2000
G1 X194.069 Y199.196 E.31761
G1 X193.936 Y199.33
G1 X193.09 Y199.642
G1 X193.223 Y199.509
G1 X201.076 Y191.656 E.33079
G1 X201.21 Y191.523
G1 X200.676 Y191.523
G1 X200.543 Y191.656
G1 X189.931 Y202.267 E.44699
G1 X189.798 Y202.401
G1 X189.623 Y202.043
G1 X189.756 Y201.909
G1 X200.009 Y191.656 E.43191
G1 X200.143 Y191.523
G1 X199.61 Y191.523
G1 X199.476 Y191.656
G1 X189.525 Y201.607 E.41918
G1 X189.392 Y201.741
G1 X189.113 Y201.486
G1 X189.247 Y201.353
G1 X198.943 Y191.656 E.40845
G1 X199.077 Y191.523
G1 X198.543 Y191.523
G1 X198.41 Y191.656
G1 X188.918 Y201.148 E.39984
G1 X188.784 Y201.282
G1 X188.396 Y201.137
G1 X188.529 Y201.003
G1 X197.876 Y191.656 E.39374
G1 X198.01 Y191.523
G1 X197.477 Y191.523
G1 X197.343 Y191.656
G1 X188.066 Y200.934 E.39081
G1 X187.932 Y201.067
G1 X187.326 Y201.14
G1 X187.46 Y201.006
G1 X196.81 Y191.656 E.39387
G1 X196.944 Y191.523
G1 X196.41 Y191.523
G1 X196.277 Y191.656
G1 X183.917 Y204.015 E.52063
G1 X183.784 Y204.149
G1 X183.784 Y203.616
G1 X183.917 Y203.482
G1 X195.743 Y191.656 E.49816
G1 X195.877 Y191.523
G1 X195.344 Y191.523
G1 X195.21 Y191.656
G1 X183.917 Y202.949 E.4757
G1 X183.784 Y203.083
G1 X183.784 Y202.549
G1 X183.917 Y202.416
G1 X194.677 Y191.656 E.45324
G1 X194.81 Y191.523
G1 X194.277 Y191.523
G1 X194.144 Y191.656
G1 X183.917 Y201.882 E.43077
G1 X183.784 Y202.016
G1 X183.784 Y201.483
G1 X183.917 Y201.349
G1 X193.61 Y191.656 E.40831
G1 X193.744 Y191.523
G1 X193.211 Y191.523
G1 X193.077 Y191.656
G1 X183.917 Y200.816 E.38585
G1 X183.784 Y200.95
G1 X183.784 Y200.416
G1 X183.917 Y200.283
M73 P29 R11
G1 X192.544 Y191.656 E.36339
G1 X192.677 Y191.523
G1 X192.144 Y191.523
G1 X192.011 Y191.656
G1 X183.917 Y199.749 E.34092
G1 X183.784 Y199.883
G1 X183.784 Y199.35
G1 X183.917 Y199.216
G1 X191.477 Y191.656 E.31846
G1 X191.611 Y191.523
G1 X191.078 Y191.523
G1 X190.944 Y191.656
G1 X183.917 Y198.683 E.296
G1 X183.784 Y198.817
G1 X183.784 Y198.283
G1 X183.917 Y198.15
G1 X190.411 Y191.656 E.27353
G1 X190.544 Y191.523
G1 X190.011 Y191.523
G1 X189.878 Y191.656
G1 X183.917 Y197.616 E.25107
G1 X183.784 Y197.75
G1 X183.784 Y197.217
G1 X183.917 Y197.083
G1 X189.344 Y191.656 E.22861
G1 X189.478 Y191.523
G1 X188.945 Y191.523
G1 X188.811 Y191.656
G1 X183.917 Y196.55 E.20614
G1 X183.784 Y196.684
G1 X183.784 Y196.15
G1 X183.917 Y196.017
G1 X188.344 Y191.59 E.18646
G1 X188.477 Y191.457
G1 X188.477 Y190.923
G1 X188.344 Y191.057
G1 X183.917 Y195.483 E.18646
G1 X183.784 Y195.617
G1 X183.784 Y195.084
G1 X183.917 Y194.95
G1 X188.344 Y190.524 E.18646
G1 X188.477 Y190.39
G1 X188.477 Y189.857
G1 X188.344 Y189.99
G1 X187.417 Y190.917 E.03902
G1 X187.284 Y191.05
G1 X187.284 Y190.517
G1 X187.417 Y190.384
G1 X188.328 Y189.473 E.03834
G1 X188.461 Y189.34
G1 X187.985 Y189.283
G1 X187.852 Y189.416
G1 X187.417 Y189.85 E.01829
; WIPE_START
M204 S8000
G1 X187.852 Y189.416 E-.23333
G1 X187.985 Y189.283 E-.07182
G1 X188.181 Y189.306 E-.07485
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-1.044 J-.625 P1  F60000
G1 X186.917 Y191.417 Z1.2
G1 Z.8
G1 E.4 F1800
G1 F12000
M204 S2000
G1 X183.917 Y194.417 E.12635
G1 X183.784 Y194.55
G1 X183.784 Y194.017
G1 X183.917 Y193.884
G1 X186.384 Y191.417 E.10389
G1 X186.517 Y191.284
G1 X185.984 Y191.284
G1 X185.85 Y191.417
G1 X183.917 Y193.35 E.08142
G1 X183.784 Y193.484
G1 X183.784 Y192.951
G1 X183.917 Y192.817
G1 X185.317 Y191.417 E.05896
G1 X185.451 Y191.284
G1 X184.917 Y191.284
G1 X184.784 Y191.417
G1 X183.917 Y192.284 E.0365
; WIPE_START
M204 S8000
G1 X184.625 Y191.577 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-.659 J1.023 P1  F60000
G1 X200.371 Y201.724 Z1.2
G1 Z.8
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.103333
G1 F15000
M204 S8000
G1 X200.21 Y201.916 E.0012
M204 S10000
G1 X200.915 Y201.212 F60000
; LINE_WIDTH: 0.106057
G1 F15000
M204 S8000
G1 X200.718 Y201.375 E.00127
; WIPE_START
G1 X200.915 Y201.212 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I.23 J-1.195 P1  F60000
G1 X192.879 Y199.664 Z1.2
G1 Z.8
G1 E.4 F1800
; LINE_WIDTH: 0.126007
G1 F15000
M204 S8000
G1 X192.705 Y199.807 E.00148
; LINE_WIDTH: 0.0986682
G1 X192.573 Y199.923 E.00077
M204 S10000
G1 X191.926 Y200.57 F60000
; LINE_WIDTH: 0.107074
G1 F15000
M204 S8000
G1 X191.729 Y200.799 E.00153
; LINE_WIDTH: 0.150002
G1 X191.619 Y200.936 E.00149
; LINE_WIDTH: 0.181203
G1 X191.56 Y201.012 E.00105
; LINE_WIDTH: 0.208224
G1 X191.502 Y201.088 E.00125
G1 X191.523 Y201.233 E.00192
; WIPE_START
G1 X191.502 Y201.088 E-.22999
G1 X191.56 Y201.012 E-.15001
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-.235 J-1.194 P1  F60000
G1 X186.151 Y202.076 Z1.2
G1 Z.8
M73 P29 R10
G1 E.4 F1800
; LINE_WIDTH: 0.089201
G1 F15000
M204 S8000
G1 X186.132 Y202.102 E.00012
; LINE_WIDTH: 0.110804
G1 X186.074 Y202.188 E.00056
; LINE_WIDTH: 0.163176
G2 X185.939 Y202.395 I4.119 J2.833 E.00235
; WIPE_START
G1 X186.074 Y202.188 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-1.217 J-.021 P1  F60000
G1 X185.951 Y209.319 Z1.2
G1 Z.8
G1 E.4 F1800
; LINE_WIDTH: 0.173878
G1 F15000
M204 S8000
G1 X185.64 Y209.583 E.00422
G1 X185.684 Y209.717 E.00146
; OBJECT_ID: 12
; COOLING_NODE: 0
; WIPE_START
G1 X185.64 Y209.583 E-.09791
G1 X185.951 Y209.319 E-.28209
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 16
M625
; start printing object, unique label id: 12
M624 AgAAAAAAAAA=
M204 S10000
G17
G3 Z1.2 I1.207 J.152 P1  F60000
G1 X197.535 Y117.281 Z1.2
G1 Z.8
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X197.475 Y117.362 E.00327
G3 X194.744 Y111.593 I-2.466 J-2.364 E.42517
G1 X194.933 Y111.584 E.00606
G3 X197.828 Y116.928 I.076 J3.415 E.24091
G1 X197.574 Y117.234 E.0128
; COOLING_NODE: 0
M204 S10000
G1 X197.221 Y117.024 F60000
G1 F13265.217
M204 S8000
G1 X197.18 Y117.079 E.00218
G3 X194.775 Y111.999 I-2.174 J-2.08 E.37467
G1 X194.938 Y111.991 E.00524
G3 X197.49 Y116.697 I.068 J3.008 E.21221
G1 X197.259 Y116.978 E.01169
; COOLING_NODE: 0
M204 S10000
G1 X196.906 Y116.768 F60000
G1 F13265.217
M204 S8000
G1 X196.886 Y116.795 E.00107
G3 X194.805 Y112.405 I-1.883 J-1.796 E.32414
G1 X194.943 Y112.398 E.00442
G3 X197.152 Y116.467 I.061 J2.601 E.18351
G1 X196.944 Y116.722 E.01058
; COOLING_NODE: 0
M204 S250
G1 X196.596 Y116.516 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G3 X194.835 Y112.796 I-1.596 J-1.521 E.2545
G1 X194.948 Y112.791 E.00336
G3 X196.637 Y116.472 I.053 J2.204 E.15296
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X196.29 Y116.795 E-.17997
G1 X195.912 Y117.013 E-.16621
G1 X195.827 Y117.042 E-.03382
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-1.15 J.399 P1  F60000
G1 X200.541 Y130.62 Z1.2
G1 Z.8
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X189.38 Y130.62 E.35888
G1 X189.38 Y128.38 E.07203
G1 X188.416 Y128.38 E.03101
G1 X188.416 Y110.416 E.57763
G1 X201.584 Y110.416 E.42342
G1 X201.584 Y128.38 E.57763
G1 X200.62 Y128.38 E.03101
G1 X200.62 Y130.62 E.07203
G1 X200.601 Y130.62 E.00061
; COOLING_NODE: 0
M204 S10000
G1 X201.017 Y131.027 F60000
G1 F13265.217
M204 S8000
G1 X188.973 Y131.027 E.38729
G1 X188.973 Y128.787 E.07203
G1 X188.009 Y128.787 E.03101
G1 X188.009 Y110.009 E.60381
G1 X201.991 Y110.009 E.4496
G1 X201.991 Y128.787 E.60381
G1 X201.027 Y128.787 E.03101
G1 X201.027 Y130.976 E.07041
; COOLING_NODE: 0
M204 S10000
G1 X201.434 Y131.21 F60000
G1 F13265.217
M204 S8000
G1 X201.434 Y131.434 E.00719
G1 X188.566 Y131.434 E.41377
G1 X188.566 Y129.194 E.07203
G1 X187.602 Y129.194 E.03101
G1 X187.602 Y109.602 E.62999
G1 X202.398 Y109.602 E.47578
G1 X202.398 Y129.194 E.62999
G1 X201.434 Y129.194 E.03101
G1 X201.434 Y131.15 E.06291
; COOLING_NODE: 1
; WIPE_START
G1 X201.434 Y131.434 E-.10782
G1 X200.717 Y131.434 E-.27218
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I.131 J1.21 P1  F60000
G1 X202.79 Y131.21 Z1.2
G1 Z.8
G1 E.4 F1800
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X206.29 Y131.21 E.10425
G1 X206.29 Y150.79 E.58322
G1 X204.11 Y150.79 E.06494
G1 X204.11 Y149.79 E.02979
G1 X203.66 Y149.79 E.0134
G1 X203.66 Y143.835 E.17737
G2 X200.34 Y143.838 I-1.661 J-.83 E.22507
G1 X200.34 Y149.79 E.17729
G1 X199.89 Y149.79 E.0134
G1 X199.89 Y150.79 E.02979
G1 X198.71 Y150.79 E.03515
G1 X198.71 Y142.997 E.23212
G2 X191.29 Y142.997 I-3.71 J.004 E.34694
G1 X191.29 Y150.79 E.23212
G1 X190.11 Y150.79 E.03515
G1 X190.11 Y149.79 E.02979
G1 X189.66 Y149.79 E.0134
G1 X189.66 Y143.835 E.17737
G2 X186.34 Y143.835 I-1.66 J-.833 E.22525
G1 X186.34 Y149.79 E.17737
G1 X185.89 Y149.79 E.0134
G1 X185.89 Y150.79 E.02979
G1 X183.71 Y150.79 E.06494
G1 X183.71 Y131.21 E.58322
G1 X187.21 Y131.21 E.10425
G1 X187.21 Y109.21 E.65531
G1 X202.79 Y109.21 E.46408
G1 X202.79 Y131.15 E.65352
; WIPE_START
M204 S8000
G1 X203.79 Y131.167 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I.208 J-1.199 P1  F60000
G1 X199.685 Y130.456 Z1.2
G1 Z.8
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42437
G1 F14156.507
M204 S8000
G1 X200.286 Y129.854 E.02565
G1 X200.286 Y129.315 E.01625
G1 X199.315 Y130.286 E.0414
G1 X198.775 Y130.286 E.01625
G1 X200.456 Y128.606 E.07162
M204 S10000
G1 X200.846 Y128.216 F60000
G1 F14156.507
M204 S8000
G1 X201.251 Y127.811 E.01725
G1 X201.251 Y127.272 E.01625
G1 X198.236 Y130.286 E.12847
G1 X197.696 Y130.286 E.01625
G1 X201.251 Y126.732 E.15145
G1 X201.251 Y126.193 E.01625
G1 X197.157 Y130.286 E.17444
G1 X196.618 Y130.286 E.01625
G1 X201.251 Y125.653 E.19743
G1 X201.251 Y125.114 E.01625
G1 X196.078 Y130.286 E.22042
G1 X195.539 Y130.286 E.01625
G1 X201.251 Y124.574 E.2434
G1 X201.251 Y124.035 E.01625
G1 X194.999 Y130.286 E.26639
G1 X194.46 Y130.286 E.01625
G1 X201.251 Y123.496 E.28938
G1 X201.251 Y122.956 E.01625
G1 X193.92 Y130.286 E.31237
G1 X193.381 Y130.286 E.01625
G1 X201.251 Y122.417 E.33535
G1 X201.251 Y121.877 E.01625
G1 X192.841 Y130.286 E.35834
G1 X192.302 Y130.286 E.01625
G1 X201.251 Y121.338 E.38133
G1 X201.251 Y120.798 E.01625
G1 X191.762 Y130.286 E.40432
G1 X191.223 Y130.286 E.01625
G1 X201.251 Y120.259 E.4273
G1 X201.251 Y119.719 E.01625
G1 X190.684 Y130.286 E.45029
G1 X190.144 Y130.286 E.01625
G1 X201.251 Y119.18 E.47328
G1 X201.251 Y118.64 E.01625
G1 X189.714 Y130.178 E.49163
G1 X189.714 Y129.638 E.01625
G1 X201.251 Y118.101 E.49163
G1 X201.251 Y117.562 E.01625
G1 X189.714 Y129.099 E.49163
M73 P30 R10
G1 X189.714 Y128.559 E.01625
G1 X201.251 Y117.022 E.49163
G1 X201.251 Y116.483 E.01625
G1 X189.687 Y128.046 E.49276
G1 X189.148 Y128.046 E.01625
G1 X201.251 Y115.943 E.51575
G1 X201.251 Y115.404 E.01625
G1 X188.749 Y127.905 E.53271
G1 X188.749 Y127.366 E.01625
G1 X201.251 Y114.864 E.53271
G1 X201.251 Y114.325 E.01625
G1 X188.749 Y126.826 E.53271
G1 X188.749 Y126.287 E.01625
G1 X196.694 Y118.342 E.33854
G3 X195.841 Y118.656 I-1.91 J-3.878 E.02744
G1 X188.749 Y125.747 E.30219
G1 X188.749 Y125.208 E.01625
G1 X195.216 Y118.741 E.27556
G3 X194.681 Y118.736 I-.224 J-4.717 E.01612
G1 X188.749 Y124.668 E.25278
G1 X188.749 Y124.129 E.01625
G1 X194.214 Y118.664 E.23288
G3 X193.792 Y118.547 I.374 J-2.168 E.01323
G1 X188.749 Y123.589 E.21488
G1 X188.749 Y123.05 E.01625
G1 X193.407 Y118.392 E.19849
G3 X193.056 Y118.204 I.764 J-1.852 E.01203
G1 X188.749 Y122.511 E.18351
G1 X188.749 Y121.971 E.01625
G1 X192.735 Y117.986 E.16982
G3 X192.442 Y117.739 I1.085 J-1.587 E.01156
G1 X188.749 Y121.432 E.15733
G1 X188.749 Y120.892 E.01625
G1 X192.176 Y117.465 E.14603
G3 X191.938 Y117.164 I1.385 J-1.336 E.01159
G1 X188.749 Y120.353 E.1359
G1 X188.749 Y119.813 E.01625
G1 X191.731 Y116.832 E.12704
G3 X191.55 Y116.473 I1.708 J-1.081 E.01213
G1 X188.749 Y119.274 E.11936
G1 X188.749 Y118.734 E.01625
G1 X191.408 Y116.076 E.11327
G3 X191.307 Y115.637 I2.144 J-.723 E.01359
G1 X188.749 Y118.195 E.10898
G1 X188.749 Y117.655 E.01625
G1 X191.256 Y115.149 E.10681
G3 X191.272 Y114.593 I4.666 J-.142 E.01676
G1 X188.749 Y117.116 E.1075
G1 X188.749 Y116.577 E.01625
G1 X191.69 Y113.636 E.12529
; WIPE_START
G1 X190.982 Y114.343 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I1.117 J-.484 P1  F60000
G1 X189.352 Y110.58 Z1.2
G1 Z.8
G1 E.4 F1800
G1 F14156.507
M204 S8000
G1 X188.749 Y111.182 E.02567
G1 X188.749 Y111.721 E.01625
G1 X189.721 Y110.749 E.04143
G1 X190.261 Y110.749 E.01625
G1 X188.749 Y112.261 E.06441
G1 X188.749 Y112.8 E.01625
G1 X190.8 Y110.749 E.0874
G1 X191.34 Y110.749 E.01625
G1 X188.749 Y113.34 E.11039
G1 X188.749 Y113.879 E.01625
G1 X191.879 Y110.749 E.13338
G1 X192.419 Y110.749 E.01625
G1 X188.749 Y114.419 E.15636
G1 X188.749 Y114.958 E.01625
G1 X192.958 Y110.749 E.17935
G1 X193.498 Y110.749 E.01625
G1 X188.749 Y115.498 E.20234
G1 X188.749 Y116.037 E.01625
G1 X194.037 Y110.749 E.22533
G1 X194.577 Y110.749 E.01625
G1 X193.912 Y111.414 E.02831
G3 X194.586 Y111.28 I.861 J2.567 E.02075
G1 X195.116 Y110.749 E.0226
G1 X195.655 Y110.749 E.01625
G1 X195.146 Y111.259 E.0217
G3 X195.64 Y111.304 I.07 J1.954 E.01499
G1 X196.195 Y110.749 E.02364
G1 X196.734 Y110.749 E.01625
G1 X196.075 Y111.409 E.02809
G3 X196.47 Y111.553 I-.524 J2.048 E.0127
G1 X197.274 Y110.749 E.03424
G1 X197.813 Y110.749 E.01625
G1 X196.832 Y111.731 E.04183
G3 X197.162 Y111.94 I-.877 J1.755 E.0118
G1 X198.353 Y110.749 E.05073
G1 X198.892 Y110.749 E.01625
G1 X197.464 Y112.177 E.06085
G3 X197.738 Y112.443 I-1.19 J1.505 E.01151
G1 X199.432 Y110.749 E.07215
G1 X199.971 Y110.749 E.01625
G1 X197.985 Y112.735 E.08463
G3 X198.202 Y113.058 I-1.504 J1.247 E.01173
G1 X200.511 Y110.749 E.09837
G1 X201.05 Y110.749 E.01625
G1 X198.392 Y113.408 E.11327
G3 X198.547 Y113.791 I-1.839 J.969 E.0125
G1 X201.251 Y111.088 E.11519
G1 X201.251 Y111.628 E.01625
G1 X198.666 Y114.212 E.11014
G3 X198.736 Y114.682 I-5.52 J1.06 E.01431
G1 X201.251 Y112.167 E.10717
G1 X201.251 Y112.706 E.01625
G1 X198.741 Y115.216 E.10695
G3 X198.651 Y115.845 I-3.903 J-.235 E.01917
G1 X201.251 Y113.246 E.11077
G1 X201.251 Y113.785 E.01625
G1 X197.705 Y117.331 E.1511
; WIPE_START
G1 X198.412 Y116.624 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-1.216 J.046 P1  F60000
G1 X199.683 Y150.114 Z1.2
G1 Z.8
G1 E.4 F1800
; FEATURE: Top surface
; LINE_WIDTH: 0.42
G1 F12000
M204 S2000
G1 X199.214 Y150.583 E.01975
G1 X199.08 Y150.716
G1 X198.784 Y150.479
G1 X198.917 Y150.346
G1 X200.133 Y149.131 E.05119
G1 X200.266 Y148.997
G1 X200.266 Y148.464
G1 X200.133 Y148.597
G1 X198.917 Y149.812 E.05119
G1 X198.784 Y149.946
G1 X198.784 Y149.413
G1 X198.917 Y149.279
G1 X200.133 Y148.064 E.05119
G1 X200.266 Y147.93
G1 X200.266 Y147.397
G1 X200.133 Y147.531
G1 X198.917 Y148.746 E.05119
G1 X198.784 Y148.88
G1 X198.784 Y148.346
G1 X198.917 Y148.213
G1 X200.133 Y146.997 E.05119
G1 X200.266 Y146.864
G1 X200.266 Y146.331
G1 X200.133 Y146.464
G1 X198.917 Y147.679 E.05119
G1 X198.784 Y147.813
G1 X198.784 Y147.28
G1 X198.917 Y147.146
G1 X200.133 Y145.931 E.05119
G1 X200.266 Y145.797
G1 X200.266 Y145.264
G1 X200.133 Y145.398
G1 X198.917 Y146.613 E.05119
G1 X198.784 Y146.747
G1 X198.784 Y146.213
G1 X198.917 Y146.08
G1 X200.133 Y144.864 E.05119
G1 X200.266 Y144.731
G1 X200.266 Y144.198
G1 X200.133 Y144.331
G1 X198.917 Y145.546 E.05119
G1 X198.784 Y145.68
G1 X198.784 Y145.147
G1 X198.917 Y145.013
G1 X200.106 Y143.824 E.05008
G1 X200.24 Y143.691
G1 X200.11 Y143.287
G1 X199.977 Y143.421
G1 X198.917 Y144.48 E.04461
G1 X198.784 Y144.614
G1 X198.784 Y144.08
G1 X198.917 Y143.947
G1 X199.936 Y142.928 E.04289
G1 X200.069 Y142.795
G1 X200.205 Y142.125
G1 X200.072 Y142.259
G1 X198.917 Y143.413 E.04863
; WIPE_START
M204 S8000
G1 X199.625 Y142.706 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-.804 J-.913 P1  F60000
G1 X190.682 Y150.583 Z1.2
G1 Z.8
G1 E.4 F1800
G1 F12000
M204 S2000
G1 X191.083 Y150.182 E.01689
G1 X191.216 Y150.048
G1 X191.216 Y149.515
G1 X191.083 Y149.648
G1 X190.317 Y150.414 E.03224
G1 X190.184 Y150.547
G1 X190.184 Y150.014
G1 X190.317 Y149.88
G1 X191.083 Y149.115 E.03224
G1 X191.216 Y148.982
G1 X191.216 Y148.448
G1 X191.083 Y148.582
G1 X190.082 Y149.583 E.04215
G1 X189.948 Y149.716
G1 X189.734 Y149.398
G1 X189.867 Y149.264
G1 X191.083 Y148.049 E.05119
G1 X191.216 Y147.915
G1 X191.216 Y147.382
G1 X191.083 Y147.515
G1 X189.867 Y148.731 E.05119
G1 X189.734 Y148.864
G1 X189.734 Y148.331
G1 X189.867 Y148.197
G1 X191.083 Y146.982 E.05119
G1 X191.216 Y146.848
G1 X191.216 Y146.315
G1 X191.083 Y146.449
G1 X189.867 Y147.664 E.05119
G1 X189.734 Y147.798
G1 X189.734 Y147.264
G1 X189.867 Y147.131
G1 X191.083 Y145.916 E.05119
G1 X191.216 Y145.782
G1 X191.216 Y145.249
G1 X191.083 Y145.382
G1 X189.867 Y146.598 E.05119
G1 X189.734 Y146.731
G1 X189.734 Y146.198
G1 X189.867 Y146.064
G1 X191.083 Y144.849 E.05119
G1 X191.216 Y144.715
G1 X191.216 Y144.182
G1 X191.083 Y144.316
G1 X189.867 Y145.531 E.05119
G1 X189.734 Y145.665
G1 X189.734 Y145.131
G1 X189.867 Y144.998
G1 X191.083 Y143.783 E.05119
G1 X191.216 Y143.649
G1 X191.216 Y143.116
G1 X191.083 Y143.249
G1 X189.867 Y144.465 E.05119
G1 X189.734 Y144.598
G1 X189.734 Y144.065
G1 X189.867 Y143.931
G1 X191.095 Y142.704 E.05171
G1 X191.229 Y142.57
G1 X191.329 Y141.937
G1 X191.195 Y142.07
G1 X190.055 Y143.211 E.04805
G1 X189.921 Y143.344
G1 X189.91 Y142.822
G1 X190.044 Y142.688
G1 X191.511 Y141.221 E.06179
; WIPE_START
M204 S8000
G1 X190.804 Y141.928 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-1.017 J-.669 P1  F60000
G1 X185.683 Y149.716 Z1.2
G1 Z.8
G1 E.4 F1800
G1 F12000
M204 S2000
G1 X184.816 Y150.583 E.03651
G1 X184.682 Y150.716
G1 X184.149 Y150.716
G1 X184.283 Y150.583
G1 X186.133 Y148.733 E.07793
G1 X186.266 Y148.599
G1 X186.266 Y148.066
G1 X186.133 Y148.199
G1 X183.917 Y150.415 E.09332
G1 X183.784 Y150.548
G1 X183.784 Y150.015
G1 X183.917 Y149.881
G1 X186.133 Y147.666 E.09332
G1 X186.266 Y147.532
G1 X186.266 Y146.999
G1 X186.133 Y147.133
G1 X183.917 Y149.348 E.09332
G1 X183.784 Y149.482
G1 X183.784 Y148.948
G1 X183.917 Y148.815
G1 X186.133 Y146.6 E.09332
G1 X186.266 Y146.466
G1 X186.266 Y145.933
G1 X186.133 Y146.066
G1 X183.917 Y148.282 E.09332
G1 X183.784 Y148.415
G1 X183.784 Y147.882
G1 X183.917 Y147.748
G1 X186.133 Y145.533 E.09332
G1 X186.266 Y145.399
G1 X186.266 Y144.866
G1 X186.133 Y145
G1 X183.917 Y147.215 E.09332
G1 X183.784 Y147.349
G1 X183.784 Y146.815
G1 X183.917 Y146.682
G1 X186.133 Y144.467 E.09332
G1 X186.266 Y144.333
G1 X186.266 Y143.8
G1 X186.133 Y143.933
G1 X183.917 Y146.148 E.09332
G1 X183.784 Y146.282
G1 X183.784 Y145.749
G1 X183.917 Y145.615
G1 X186.002 Y143.53 E.08783
G1 X186.136 Y143.397
G1 X186.068 Y142.932
G1 X185.934 Y143.065
G1 X183.917 Y145.082 E.08495
G1 X183.784 Y145.216
G1 X183.784 Y144.682
G1 X183.917 Y144.549
G1 X186.006 Y142.46 E.088
; WIPE_START
M204 S8000
G1 X185.299 Y143.167 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-.417 J1.143 P1  F60000
G1 X205.613 Y150.583 Z1.2
G1 Z.8
G1 E.4 F1800
G1 F12000
M204 S2000
G1 X206.083 Y150.113 E.01979
G1 X206.216 Y149.979
G1 X206.216 Y149.446
G1 X206.083 Y149.58
G1 X205.08 Y150.583 E.04225
G1 X204.946 Y150.716
G1 X204.413 Y150.716
G1 X204.546 Y150.583
G1 X206.083 Y149.046 E.06471
G1 X206.216 Y148.913
G1 X206.216 Y148.379
G1 X206.083 Y148.513
G1 X204.317 Y150.278 E.07436
G1 X204.184 Y150.412
G1 X204.184 Y149.879
G1 X204.317 Y149.745
G1 X206.083 Y147.98 E.07436
G1 X206.216 Y147.846
G1 X206.216 Y147.313
G1 X206.083 Y147.447
G1 X203.947 Y149.583 E.08998
G1 X203.813 Y149.716
G1 X203.734 Y149.262
G1 X203.867 Y149.129
G1 X206.083 Y146.913 E.09332
G1 X206.216 Y146.78
G1 X206.216 Y146.246
G1 X206.083 Y146.38
G1 X203.867 Y148.595 E.09332
G1 X203.734 Y148.729
G1 X203.734 Y148.196
G1 X203.867 Y148.062
G1 X206.083 Y145.847 E.09332
G1 X206.216 Y145.713
G1 X206.216 Y145.18
G1 X206.083 Y145.314
G1 X203.867 Y147.529 E.09332
G1 X203.734 Y147.662
G1 X203.734 Y147.129
G1 X203.867 Y146.996
G1 X206.083 Y144.78 E.09332
G1 X206.216 Y144.647
G1 X206.216 Y144.113
G1 X206.083 Y144.247
G1 X203.867 Y146.462 E.09332
G1 X203.734 Y146.596
G1 X203.734 Y146.063
G1 X203.867 Y145.929
G1 X206.083 Y143.714 E.09332
G1 X206.216 Y143.58
G1 X206.216 Y143.047
G1 X206.083 Y143.181
G1 X203.867 Y145.396 E.09332
G1 X203.734 Y145.529
G1 X203.734 Y144.996
G1 X203.867 Y144.862
G1 X206.083 Y142.647 E.09332
G1 X206.216 Y142.514
G1 X206.216 Y141.98
G1 X206.083 Y142.114
G1 X203.867 Y144.329 E.09332
G1 X203.734 Y144.463
G1 X203.8 Y143.863
G1 X203.934 Y143.729
G1 X206.083 Y141.581 E.09051
G1 X206.216 Y141.447
G1 X206.216 Y140.914
G1 X206.083 Y141.047
G1 X204.066 Y143.064 E.08495
G1 X203.932 Y143.198
G1 X203.889 Y142.708
G1 X204.023 Y142.574
G1 X206.083 Y140.514 E.08677
M73 P31 R10
G1 X206.216 Y140.381
G1 X206.216 Y139.847
G1 X206.083 Y139.981
G1 X203.893 Y142.17 E.09223
G1 X203.76 Y142.304
G1 X203.569 Y141.961
G1 X203.703 Y141.827
G1 X206.083 Y139.448 E.10025
G1 X206.216 Y139.314
G1 X206.216 Y138.781
G1 X206.083 Y138.914
G1 X203.46 Y141.537 E.11048
G1 X203.326 Y141.671
G1 X203.034 Y141.429
G1 X203.168 Y141.296
G1 X206.083 Y138.381 E.12277
G1 X206.216 Y138.248
G1 X206.216 Y137.714
G1 X206.083 Y137.848
G1 X202.825 Y141.105 E.13721
G1 X202.692 Y141.239
G1 X202.287 Y141.111
G1 X202.42 Y140.977
G1 X206.083 Y137.315 E.15427
G1 X206.216 Y137.181
G1 X206.216 Y136.648
G1 X206.083 Y136.781
G1 X201.928 Y140.936 E.175
G1 X201.795 Y141.069
G1 X201.125 Y141.206
G1 X201.258 Y141.072
G1 X206.083 Y136.248 E.20321
G1 X206.216 Y136.115
G1 X206.216 Y135.581
G1 X206.083 Y135.715
G1 X198.915 Y142.883 E.30195
G1 X198.781 Y143.017
G1 X198.736 Y142.528
G1 X198.87 Y142.394
G1 X206.083 Y135.182 E.30383
G1 X206.216 Y135.048
G1 X206.216 Y134.515
G1 X206.083 Y134.648
G1 X198.775 Y141.956 E.30784
G1 X198.641 Y142.09
G1 X198.507 Y141.691
G1 X198.641 Y141.557
G1 X206.083 Y134.115 E.31348
G1 X206.216 Y133.982
G1 X206.216 Y133.448
G1 X206.083 Y133.582
G1 X198.474 Y141.191 E.32053
G1 X198.34 Y141.325
G1 X198.143 Y140.988
G1 X198.277 Y140.855
G1 X206.083 Y133.049 E.32883
G1 X206.216 Y132.915
G1 X206.216 Y132.382
G1 X206.083 Y132.515
G1 X198.052 Y140.546 E.3383
G1 X197.918 Y140.68
G1 X197.668 Y140.397
G1 X197.801 Y140.263
G1 X206.083 Y131.982 E.34884
G1 X206.216 Y131.848
G1 X206.216 Y131.315
G1 X206.083 Y131.449
G1 X197.525 Y140.006 E.36048
G1 X197.391 Y140.14
G1 X197.089 Y139.909
G1 X197.222 Y139.776
G1 X205.581 Y131.417 E.35209
G1 X205.714 Y131.284
G1 X205.181 Y131.284
G1 X205.048 Y131.417
G1 X196.893 Y139.572 E.3435
G1 X196.76 Y139.705
G1 X196.401 Y139.531
G1 X196.535 Y139.397
G1 X204.514 Y131.417 E.33614
G1 X204.648 Y131.284
G1 X204.115 Y131.284
G1 X203.981 Y131.417
G1 X196.144 Y139.254 E.33013
G1 X196.01 Y139.388
G1 X195.582 Y139.283
G1 X195.716 Y139.149
G1 X203.448 Y131.417 E.3257
G1 X203.581 Y131.284
G1 X203.048 Y131.284
G1 X202.915 Y131.417
G1 X195.241 Y139.091 E.32324
G1 X195.107 Y139.224
G1 X194.571 Y139.227
G1 X194.705 Y139.094
G1 X202.583 Y131.216 E.33184
G1 X202.716 Y131.082
G1 X202.716 Y130.549
G1 X202.583 Y130.683
G1 X201.656 Y131.609 E.03902
G1 X201.523 Y131.743
G1 X201.523 Y131.21
G1 X201.656 Y131.076
G1 X202.583 Y130.15 E.03902
G1 X202.716 Y130.016
G1 X202.716 Y129.483
G1 X202.583 Y129.616
G1 X201.656 Y130.543 E.03902
G1 X201.523 Y130.676
G1 X201.523 Y130.143
G1 X201.656 Y130.009
G1 X202.25 Y129.416 E.02499
; WIPE_START
M204 S8000
G1 X201.656 Y130.009 E-.31883
G1 X201.542 Y130.123 E-.06118
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-1.216 J.053 P1  F60000
G1 X201.609 Y131.656 Z1.2
G1 Z.8
G1 E.4 F1800
G1 F12000
M204 S2000
G1 X194.069 Y139.196 E.31761
G1 X193.936 Y139.33
G1 X193.09 Y139.642
G1 X193.223 Y139.509
G1 X201.076 Y131.656 E.33079
G1 X201.21 Y131.523
G1 X200.676 Y131.523
G1 X200.543 Y131.656
G1 X189.931 Y142.268 E.447
G1 X189.798 Y142.401
G1 X189.621 Y142.044
G1 X189.755 Y141.911
G1 X200.009 Y131.656 E.43197
G1 X200.143 Y131.523
G1 X199.61 Y131.523
G1 X199.476 Y131.656
G1 X189.526 Y141.606 E.41913
G1 X189.393 Y141.74
G1 X189.113 Y141.486
G1 X189.247 Y141.352
G1 X198.943 Y131.656 E.40844
G1 X199.077 Y131.523
G1 X198.543 Y131.523
G1 X198.41 Y131.656
G1 X188.918 Y141.148 E.39985
G1 X188.784 Y141.282
G1 X188.396 Y141.136
G1 X188.53 Y141.003
G1 X197.876 Y131.656 E.39371
G1 X198.01 Y131.523
G1 X197.477 Y131.523
G1 X197.343 Y131.656
G1 X188.066 Y140.934 E.39081
G1 X187.932 Y141.067
G1 X187.326 Y141.14
G1 X187.46 Y141.007
G1 X196.81 Y131.656 E.39388
G1 X196.944 Y131.523
G1 X196.41 Y131.523
G1 X196.277 Y131.656
G1 X183.917 Y144.015 E.52063
G1 X183.784 Y144.149
G1 X183.784 Y143.616
G1 X183.917 Y143.482
G1 X195.743 Y131.656 E.49816
G1 X195.877 Y131.523
G1 X195.344 Y131.523
G1 X195.21 Y131.656
G1 X183.917 Y142.949 E.4757
G1 X183.784 Y143.083
G1 X183.784 Y142.549
G1 X183.917 Y142.416
G1 X194.677 Y131.656 E.45324
G1 X194.81 Y131.523
G1 X194.277 Y131.523
G1 X194.144 Y131.656
G1 X183.917 Y141.882 E.43077
G1 X183.784 Y142.016
G1 X183.784 Y141.483
G1 X183.917 Y141.349
G1 X193.61 Y131.656 E.40831
G1 X193.744 Y131.523
G1 X193.211 Y131.523
G1 X193.077 Y131.656
G1 X183.917 Y140.816 E.38585
G1 X183.784 Y140.95
G1 X183.784 Y140.416
G1 X183.917 Y140.283
G1 X192.544 Y131.656 E.36339
G1 X192.677 Y131.523
G1 X192.144 Y131.523
G1 X192.011 Y131.656
G1 X183.917 Y139.749 E.34092
G1 X183.784 Y139.883
G1 X183.784 Y139.35
G1 X183.917 Y139.216
G1 X191.477 Y131.656 E.31846
G1 X191.611 Y131.523
G1 X191.078 Y131.523
G1 X190.944 Y131.656
G1 X183.917 Y138.683 E.296
G1 X183.784 Y138.817
G1 X183.784 Y138.283
G1 X183.917 Y138.15
G1 X190.411 Y131.656 E.27353
G1 X190.544 Y131.523
G1 X190.011 Y131.523
G1 X189.878 Y131.656
G1 X183.917 Y137.616 E.25107
G1 X183.784 Y137.75
G1 X183.784 Y137.217
G1 X183.917 Y137.083
G1 X189.344 Y131.656 E.22861
G1 X189.478 Y131.523
G1 X188.945 Y131.523
G1 X188.811 Y131.656
G1 X183.917 Y136.55 E.20614
G1 X183.784 Y136.683
G1 X183.784 Y136.15
G1 X183.917 Y136.017
G1 X188.344 Y131.59 E.18646
G1 X188.477 Y131.457
G1 X188.477 Y130.923
G1 X188.344 Y131.057
G1 X183.917 Y135.483 E.18646
G1 X183.784 Y135.617
G1 X183.784 Y135.084
G1 X183.917 Y134.95
G1 X188.344 Y130.524 E.18646
G1 X188.477 Y130.39
G1 X188.477 Y129.857
G1 X188.344 Y129.99
G1 X187.417 Y130.917 E.03902
G1 X187.284 Y131.05
G1 X187.284 Y130.517
G1 X187.417 Y130.384
G1 X188.328 Y129.473 E.03834
G1 X188.461 Y129.34
G1 X187.985 Y129.282
G1 X187.852 Y129.416
G1 X187.417 Y129.85 E.01829
; WIPE_START
M204 S8000
G1 X187.852 Y129.416 E-.23333
G1 X187.985 Y129.282 E-.07182
G1 X188.181 Y129.306 E-.07485
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-1.044 J-.625 P1  F60000
G1 X186.917 Y131.417 Z1.2
G1 Z.8
G1 E.4 F1800
G1 F12000
M204 S2000
G1 X183.917 Y134.417 E.12635
G1 X183.784 Y134.55
G1 X183.784 Y134.017
G1 X183.917 Y133.884
G1 X186.384 Y131.417 E.10389
G1 X186.517 Y131.284
G1 X185.984 Y131.284
G1 X185.85 Y131.417
G1 X183.917 Y133.35 E.08142
G1 X183.784 Y133.484
G1 X183.784 Y132.951
G1 X183.917 Y132.817
G1 X185.317 Y131.417 E.05896
G1 X185.451 Y131.284
G1 X184.917 Y131.284
G1 X184.784 Y131.417
G1 X183.917 Y132.284 E.0365
; WIPE_START
M204 S8000
G1 X184.625 Y131.577 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-.658 J1.023 P1  F60000
G1 X200.381 Y141.713 Z1.2
G1 Z.8
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.104298
G1 F15000
M204 S8000
G1 X200.212 Y141.915 E.00128
M204 S10000
G1 X200.914 Y141.212 F60000
; LINE_WIDTH: 0.10597
G1 F15000
M204 S8000
G1 X200.719 Y141.375 E.00127
; WIPE_START
G1 X200.914 Y141.212 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I.23 J-1.195 P1  F60000
G1 X192.879 Y139.664 Z1.2
G1 Z.8
G1 E.4 F1800
; LINE_WIDTH: 0.126007
G1 F15000
M204 S8000
G1 X192.705 Y139.807 E.00148
; LINE_WIDTH: 0.0986682
G1 X192.573 Y139.923 E.00077
M204 S10000
G1 X191.926 Y140.57 F60000
; LINE_WIDTH: 0.107074
G1 F15000
M204 S8000
G1 X191.729 Y140.799 E.00153
; LINE_WIDTH: 0.150002
G1 X191.619 Y140.936 E.00149
; LINE_WIDTH: 0.181203
G1 X191.56 Y141.012 E.00105
; LINE_WIDTH: 0.208224
G1 X191.502 Y141.088 E.00125
G1 X191.523 Y141.233 E.00192
; WIPE_START
G1 X191.502 Y141.088 E-.22999
G1 X191.56 Y141.012 E-.15001
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-.235 J-1.194 P1  F60000
G1 X186.151 Y142.077 Z1.2
G1 Z.8
G1 E.4 F1800
; LINE_WIDTH: 0.0889034
G1 F15000
M204 S8000
G1 X186.133 Y142.1 E.00011
; LINE_WIDTH: 0.108526
G1 X186.079 Y142.18 E.0005
; LINE_WIDTH: 0.157037
G2 X185.939 Y142.393 I5.445 J3.73 E.0023
; WIPE_START
G1 X186.079 Y142.18 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-1.217 J.013 P1  F60000
G1 X186.151 Y149.15 Z1.2
G1 Z.8
G1 E.4 F1800
; LINE_WIDTH: 0.175179
G1 F15000
M204 S8000
G1 X185.64 Y149.583 E.007
G1 X185.684 Y149.717 E.00148
; OBJECT_ID: 8
; COOLING_NODE: 0
; WIPE_START
G1 X185.64 Y149.583 E-.0663
G1 X186.151 Y149.15 E-.3137
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 12
M625
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z1.2 I.734 J-.971 P1  F60000
G1 X141.848 Y115.684 Z1.2
G1 Z.8
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X141.848 Y174.884 E1.90366
G1 X140.152 Y174.884 E.05456
G1 X140.152 Y115.684 E1.90366
M73 P32 R10
G1 X121.376 Y115.684 E.60377
G1 X121.376 Y113.516 E.0697
G1 X157.584 Y113.516 E1.16432
G1 X157.584 Y115.684 E.0697
G1 X155.848 Y115.684 E.05581
G1 X155.848 Y174.884 E1.90366
G1 X154.152 Y174.884 E.05456
G1 X154.152 Y115.684 E1.90366
G1 X141.908 Y115.684 E.3937
; COOLING_NODE: 0
M204 S10000
G1 X142.255 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X142.255 Y175.291 E1.90366
G1 X141.332 Y175.291 E.02969
G1 X141.332 Y185.666 E.33362
G1 X141 Y185.981 E.01471
G1 X140.668 Y185.666 E.01472
G1 X140.668 Y175.291 E.33362
G1 X139.745 Y175.291 E.02969
G1 X139.745 Y116.091 E1.90366
G1 X120.969 Y116.091 E.60377
G1 X120.969 Y113.109 E.09588
G1 X157.991 Y113.109 E1.1905
G1 X157.991 Y116.091 E.09588
G1 X156.255 Y116.091 E.05581
G1 X156.255 Y175.291 E1.90366
G1 X155.332 Y175.291 E.02969
G1 X155.332 Y185.666 E.33362
G1 X155 Y185.981 E.01471
G1 X154.668 Y185.666 E.01472
G1 X154.668 Y175.291 E.33362
G1 X153.745 Y175.291 E.02969
G1 X153.745 Y116.091 E1.90366
G1 X142.315 Y116.091 E.36752
; COOLING_NODE: 0
M204 S10000
G1 X142.662 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X142.662 Y174.902 E1.87806
G1 X143.27 Y174.902 E.01953
G1 X143.27 Y175.698 E.02559
G1 X141.739 Y175.698 E.04921
G1 X141.739 Y185.841 E.32617
G1 X141.423 Y186.141 E.01403
G1 X141.423 Y187.004 E.02777
G3 X141 Y187.292 I-2.171 J-2.737 E.01645
G3 X140.577 Y187.004 I1.823 J-3.133 E.01645
G1 X140.577 Y186.141 E.02777
G1 X140.261 Y185.841 E.01403
G1 X140.261 Y175.698 E.32617
G1 X138.73 Y175.698 E.04921
G1 X138.73 Y174.902 E.02559
G1 X139.338 Y174.902 E.01953
G1 X139.338 Y116.498 E1.87806
G1 X120.562 Y116.498 E.60377
G1 X120.562 Y112.702 E.12206
G1 X158.398 Y112.702 E1.21668
G1 X158.398 Y116.498 E.12206
G1 X156.662 Y116.498 E.05581
G1 X156.662 Y174.902 E1.87806
G1 X157.27 Y174.902 E.01953
G1 X157.27 Y175.698 E.02559
G1 X155.739 Y175.698 E.04921
G1 X155.739 Y185.841 E.32617
G1 X155.423 Y186.141 E.01403
G1 X155.423 Y186.504 E.01169
G3 X155 Y186.79 I-2.347 J-3.02 E.01641
G3 X154.577 Y186.504 I1.926 J-3.307 E.01641
G1 X154.577 Y186.141 E.01169
G1 X154.261 Y185.841 E.01403
G1 X154.261 Y175.698 E.32617
G1 X152.73 Y175.698 E.04921
G1 X152.73 Y174.902 E.02559
G1 X153.338 Y174.902 E.01953
G1 X153.338 Y116.498 E1.87806
G1 X142.722 Y116.498 E.34134
; COOLING_NODE: 0
M204 S250
G1 X143.055 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F3630
M204 S5000
G1 X143.055 Y174.51 E1.7163
G1 X143.662 Y174.51 E.01809
G1 X143.662 Y176.09 E.04706
G1 X142.131 Y176.09 E.04559
G1 X142.131 Y186.01 E.29547
G1 X141.815 Y186.31 E.01299
G1 X141.815 Y187.197 E.02643
G3 X141.083 Y187.677 I-1.909 J-2.111 E.02619
G1 X141.019 Y187.689 E.00193
G3 X140.667 Y187.552 I.029 J-.594 E.01143
G3 X140.185 Y187.197 I3.233 J-4.888 E.01784
G1 X140.185 Y186.31 E.02643
G1 X139.869 Y186.01 E.01299
G1 X139.869 Y176.09 E.29547
G1 X138.338 Y176.09 E.04559
G1 X138.338 Y174.51 E.04706
G1 X138.945 Y174.51 E.01809
G1 X138.945 Y116.89 E1.7163
G1 X120.169 Y116.89 E.55927
G1 X120.169 Y112.31 E.13642
G1 X158.79 Y112.31 E1.15037
G1 X158.79 Y116.89 E.13642
G1 X157.055 Y116.89 E.05169
M73 P33 R10
G1 X157.055 Y174.51 E1.7163
G1 X157.662 Y174.51 E.01809
G1 X157.662 Y176.09 E.04706
G1 X156.131 Y176.09 E.04559
G1 X156.131 Y186.01 E.29547
G1 X155.815 Y186.31 E.01299
G1 X155.815 Y186.697 E.01154
G3 X155.052 Y187.184 I-1.762 J-1.917 E.02708
G3 X154.74 Y187.096 I-.045 J-.442 E.0099
G3 X154.185 Y186.697 I2.696 J-4.325 E.02037
G1 X154.185 Y186.31 E.01154
G1 X153.869 Y186.01 E.01299
G1 X153.869 Y176.09 E.29547
G1 X152.338 Y176.09 E.04559
G1 X152.338 Y174.51 E.04706
G1 X152.945 Y174.51 E.01809
G1 X152.945 Y116.89 E1.7163
G1 X143.115 Y116.89 E.29283
; WIPE_START
G1 F12000
M204 S8000
G1 X143.113 Y117.89 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-1.216 J-.045 P1  F60000
G1 X141 Y175.087 Z1.2
G1 Z.8
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.3003
G1 F15000
M204 S8000
G1 X141 Y185.523 E.21217
G1 X141.045 Y185.658 E.00289
M204 S10000
G1 X141.219 Y186.174 F60000
; LINE_WIDTH: 0.324858
G1 F15000
M204 S8000
G1 X141.164 Y186.25 E.0021
; LINE_WIDTH: 0.369493
G1 X141.11 Y186.327 E.00243
; LINE_WIDTH: 0.414128
G1 F14547.119
G1 X141.055 Y186.404 E.00276
; LINE_WIDTH: 0.458763
G1 F12985.685
G1 X141 Y186.48 E.00309
; LINE_WIDTH: 0.480399
G1 F12343.472
G1 X141 Y186.791 E.01073
G1 X141.103 Y186.989 E.00772
; WIPE_START
G1 X141 Y186.791 E-.15901
G1 X141 Y186.48 E-.22099
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I.021 J1.217 P1  F60000
G1 X154.781 Y186.238 Z1.2
G1 Z.8
G1 E.4 F1800
; LINE_WIDTH: 0.292661
G1 F15000
M204 S8000
G2 X154.98 Y186.389 I.588 J-.571 E.00494
G2 X155.219 Y186.239 I-.094 J-.414 E.00568
M204 S10000
G1 X155.045 Y185.658 F60000
; LINE_WIDTH: 0.3003
G1 F15000
M204 S8000
G1 X155 Y185.523 E.00289
G1 X155 Y175.087 E.21217
; WIPE_START
G1 X155 Y176.087 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I1.217 J0 P1  F60000
G1 X155 Y174.035 Z1.2
G1 Z.8
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.57832
G1 F10085.918
M204 S8000
G1 X155 Y115.54 E2.47392
; WIPE_START
G1 X155 Y116.54 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-1.182 J-.288 P1  F60000
G1 X141 Y174.035 Z1.2
G1 Z.8
G1 E.4 F1800
G1 F10085.918
M204 S8000
G1 X141 Y115.54 E2.47392
; WIPE_START
G1 X141 Y116.54 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-1.217 J-.01 P1  F60000
G1 X140.544 Y174.492 Z1.2
G1 Z.8
G1 E.4 F1800
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X141.456 Y174.492 E.02718
G1 X141.456 Y115.48 E1.75771
G1 X141.523 Y115.336 E.00473
G1 X141.645 Y115.292 E.00386
G1 X154.355 Y115.292 E.37859
G1 X154.518 Y115.384 E.00557
G1 X154.544 Y115.48 E.00296
G1 X154.544 Y174.492 E1.75771
G1 X155.456 Y174.492 E.02718
G1 X155.456 Y115.48 E1.75771
G1 X155.523 Y115.336 E.00473
G1 X155.645 Y115.292 E.00386
G1 X157.192 Y115.292 E.04608
G1 X157.192 Y113.908 E.04121
G1 X121.768 Y113.908 E1.05513
G1 X121.768 Y115.292 E.04121
G1 X140.355 Y115.292 E.55364
G1 X140.518 Y115.384 E.00557
G1 X140.544 Y115.48 E.00296
G1 X140.544 Y174.432 E1.75592
; WIPE_START
G1 X140.544 Y173.432 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I1.217 J.01 P1  F60000
G1 X141 Y115.48 Z1.2
G1 Z.8
G1 E.4 F1800
; LINE_WIDTH: 0.559464
G1 F10454.101
M204 S8000
G1 X141.039 Y115.408 E.00335
; LINE_WIDTH: 0.521752
G1 F11277.46
G1 X141.077 Y115.335 E.00311
; LINE_WIDTH: 0.484039
G1 F12241.601
G1 X141.116 Y115.263 E.00286
; LINE_WIDTH: 0.446327
G1 F13386.01
G1 X141.155 Y115.191 E.00262
; LINE_WIDTH: 0.448357
G1 F13318.973
G1 X141.282 Y115.08 E.0054
; LINE_WIDTH: 0.49013
G1 F12074.864
G1 X141.409 Y114.969 E.00596
; LINE_WIDTH: 0.545964
G1 F10734.657
G1 X141.536 Y114.858 E.0067
G1 X141.645 Y114.852 E.00435
G1 X154.355 Y114.852 E.50507
; LINE_WIDTH: 0.525099
G1 F11199.176
G1 X154.477 Y114.917 E.00527
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X154.599 Y114.983 E.00481
; LINE_WIDTH: 0.431029
G1 F13913.613
G3 X154.845 Y115.191 I-.156 J.436 E.0101
; LINE_WIDTH: 0.446327
G1 F13386.01
G1 X154.884 Y115.263 E.00262
; LINE_WIDTH: 0.484039
G1 F12241.601
G1 X154.923 Y115.335 E.00286
; LINE_WIDTH: 0.521752
G1 F11277.46
G1 X154.961 Y115.408 E.00311
; LINE_WIDTH: 0.559464
G1 F10454.101
G1 X155 Y115.48 E.00335
G1 X155.039 Y115.408 E.00335
; LINE_WIDTH: 0.521752
G1 F11277.46
G1 X155.077 Y115.335 E.00311
; LINE_WIDTH: 0.484039
G1 F12241.601
G1 X155.116 Y115.263 E.00286
; LINE_WIDTH: 0.446327
G1 F13386.01
G1 X155.155 Y115.191 E.00262
; LINE_WIDTH: 0.448357
G1 F13318.973
G1 X155.282 Y115.08 E.0054
; LINE_WIDTH: 0.49013
G1 F12074.864
G1 X155.409 Y114.969 E.00596
; LINE_WIDTH: 0.546394
G1 F10725.49
G1 X155.536 Y114.858 E.00671
G3 X156.752 Y114.852 I1.09 J95.188 E.04836
G1 X156.752 Y114.348 E.02001
G1 X155.645 Y114.348 E.04402
; LINE_WIDTH: 0.525099
G1 F11199.176
G1 X155.43 Y114.327 E.00823
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X155.215 Y114.306 E.00751
; LINE_WIDTH: 0.441012
G1 F13564.713
G1 X155 Y114.285 E.00679
G1 X154.785 Y114.306 E.00679
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X154.57 Y114.327 E.00751
; LINE_WIDTH: 0.545769
G1 F10738.814
G1 X154.355 Y114.348 E.00858
G1 X141.645 Y114.348 E.50488
; LINE_WIDTH: 0.525099
G1 F11199.176
G1 X141.43 Y114.327 E.00823
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X141.215 Y114.306 E.00751
; LINE_WIDTH: 0.441012
G1 F13564.713
G1 X141 Y114.285 E.00679
G1 X140.785 Y114.306 E.00679
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X140.57 Y114.327 E.00751
; LINE_WIDTH: 0.545998
G1 F10733.936
G1 X140.355 Y114.348 E.00858
G1 X122.208 Y114.348 E.72117
G1 X122.208 Y114.852 E.02
G1 X140.355 Y114.852 E.72117
; LINE_WIDTH: 0.525099
G1 F11199.176
G1 X140.477 Y114.917 E.00527
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X140.599 Y114.983 E.00481
; LINE_WIDTH: 0.431029
G1 F13913.613
G3 X140.845 Y115.191 I-.156 J.436 E.0101
; LINE_WIDTH: 0.446327
G1 F13386.01
G1 X140.877 Y115.25 E.00214
; LINE_WIDTH: 0.484039
G1 F12241.601
G1 X140.909 Y115.309 E.00234
; LINE_WIDTH: 0.521752
G1 F11277.46
G1 X140.94 Y115.368 E.00254
; LINE_WIDTH: 0.559464
G1 F10454.101
G1 X140.972 Y115.427 E.00274
M204 S10000
G1 X141.031 Y114.665 F60000
; LINE_WIDTH: 0.5313
G1 F11056.964
M204 S8000
G2 X141.031 Y114.77 I-.025 J.053 E.00903
; WIPE_START
G1 X140.969 Y114.771 E-.0956
G1 X140.939 Y114.718 E-.0948
G1 X140.969 Y114.665 E-.0948
G1 X141.031 Y114.665 E-.0948
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I0 J1.217 P1  F60000
G1 X155.031 Y114.665 Z1.2
G1 Z.8
G1 E.4 F1800
G1 F11056.964
M204 S8000
G2 X155.031 Y114.77 I-.025 J.053 E.00903
; COOLING_NODE: 0
; WIPE_START
G1 X154.969 Y114.771 E-.0956
G1 X154.939 Y114.718 E-.0948
G1 X154.969 Y114.665 E-.0948
G1 X155.031 Y114.665 E-.0948
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I-.031 J-1.217 P1  F60000
G1 X114.624 Y115.684 Z1.2
G1 Z.8
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X112.416 Y115.684 E.07101
G1 X112.416 Y113.516 E.0697
G1 X114.624 Y113.516 E.07101
G1 X114.624 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X115.031 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X112.009 Y116.091 E.09719
G1 X112.009 Y113.109 E.09588
G1 X115.031 Y113.109 E.09719
G1 X115.031 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X115.438 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X111.602 Y116.498 E.12337
G1 X111.602 Y112.702 E.12206
G1 X115.438 Y112.702 E.12337
G1 X115.438 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X115.831 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F3630
M204 S5000
G1 X111.21 Y116.89 E.13763
G1 X111.21 Y112.31 E.13642
G1 X115.831 Y112.31 E.13763
G1 X115.831 Y116.83 E.13464
; WIPE_START
G1 F12000
M204 S8000
G1 X114.831 Y116.843 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.2 I1.135 J-.438 P1  F60000
G1 X114.232 Y115.292 Z1.2
G1 Z.8
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X114.232 Y113.908 E.04121
G1 X112.808 Y113.908 E.04242
G1 X112.808 Y115.292 E.04121
G1 X114.172 Y115.292 E.04063
M204 S10000
G1 X113.792 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
M73 P34 R10
G1 X113.792 Y114.348 E.02
G1 X113.248 Y114.348 E.02161
G1 X113.248 Y114.852 E.02
G1 X113.732 Y114.852 E.01923
; CHANGE_LAYER
; Z_HEIGHT: 1
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F10731.32
G1 X113.248 Y114.852 E-.18382
G1 X113.248 Y114.348 E-.19122
G1 X113.261 Y114.348 E-.00497
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 5/27
; update layer progress
M73 L5
M991 S0 P4 ;notify layer change
M106 S58.65
; OBJECT_ID: 16
; COOLING_NODE: 0
; start printing object, unique label id: 16
M624 BAAAAAAAAAA=
M204 S10000
G17
G3 Z1.2 I-.751 J.958 P1  F60000
G1 X195.002 Y178.415 Z1.2
G1 Z1
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X194.745 Y178.404 E.00827
G3 X194.575 Y171.609 I.255 J-3.406 E.32318
G1 X194.915 Y171.583 E.01096
G3 X195.085 Y178.413 I.085 J3.415 E.34507
G1 X195.062 Y178.413 E.00074
; COOLING_NODE: 0
M204 S10000
G1 X195.012 Y178.008 F60000
G1 F13265.217
M204 S8000
G1 X194.775 Y177.998 E.00762
G3 X194.626 Y172.013 I.224 J-3 E.28464
G1 X194.925 Y171.991 E.00965
G3 X195.075 Y178.006 I.075 J3.008 E.30392
G1 X195.072 Y178.006 E.00009
; COOLING_NODE: 0
M204 S10000
G1 X195.022 Y177.601 F60000
G1 F13265.217
M204 S8000
G1 X194.806 Y177.592 E.00696
G3 X194.676 Y172.417 I.194 J-2.594 E.2461
G1 X194.935 Y172.398 E.00835
G3 X195.082 Y177.598 I.065 J2.6 E.26222
; COOLING_NODE: 0
M204 S250
G1 X195.033 Y177.208 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X194.617 Y177.174 E.01245
G3 X194.725 Y172.807 I.383 J-2.175 E.18702
G1 X194.945 Y172.79 E.00657
G3 X195.093 Y177.206 I.055 J2.208 E.20556
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X194.617 Y177.174 E-.18138
G1 X194.192 Y177.057 E-.16724
G1 X194.119 Y177.02 E-.03138
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.4 I-1.083 J.555 P1  F60000
G1 X201.584 Y191.584 Z1.4
G1 Z1
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y191.584 E.42342
G1 X188.416 Y170.416 E.68067
G1 X201.584 Y170.416 E.42342
G1 X201.584 Y191.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y191.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y191.991 E.4496
G1 X188.009 Y170.009 E.70685
G1 X201.991 Y170.009 E.4496
G1 X201.991 Y191.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y192.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y192.398 E.47578
G1 X187.602 Y169.602 E.73303
G1 X202.398 Y169.602 E.47578
G1 X202.398 Y192.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y192.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y192.79 E.46408
G1 X187.21 Y169.21 E.70237
G1 X202.79 Y169.21 E.46408
G1 X202.79 Y192.73 E.70058
; object ids of layer 5 start: 8,12,16
M624 BwAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer5 end: 8,12,16
M625
; WIPE_START
M204 S8000
G1 X201.79 Y192.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.4 I1.215 J-.077 P1  F60000
G1 X201.42 Y186.884 Z1.4
G1 Z1
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42179
G1 F14252.909
M204 S8000
G1 X188.749 Y174.213 E.53628
G1 X188.749 Y174.749 E.01604
G1 X201.251 Y187.25 E.5291
G1 X201.251 Y187.786 E.01604
G1 X188.749 Y175.285 E.5291
G1 X188.749 Y175.821 E.01604
G1 X201.251 Y188.322 E.5291
G1 X201.251 Y188.858 E.01604
G1 X188.749 Y176.357 E.5291
G1 X188.749 Y176.892 E.01604
G1 X201.251 Y189.393 E.5291
G1 X201.251 Y189.929 E.01604
G1 X188.749 Y177.428 E.5291
G1 X188.749 Y177.964 E.01604
G1 X201.251 Y190.465 E.5291
G1 X201.251 Y191.001 E.01604
G1 X188.749 Y178.5 E.5291
G1 X188.749 Y179.036 E.01604
G1 X200.964 Y191.251 E.51699
G1 X200.429 Y191.251 E.01604
G1 X188.749 Y179.571 E.49431
G1 X188.749 Y180.107 E.01604
G1 X199.893 Y191.251 E.47164
G1 X199.357 Y191.251 E.01604
G1 X188.749 Y180.643 E.44896
G1 X188.749 Y181.179 E.01604
G1 X198.821 Y191.251 E.42628
G1 X198.285 Y191.251 E.01604
G1 X188.749 Y181.715 E.4036
G1 X188.749 Y182.25 E.01604
G1 X197.75 Y191.251 E.38093
G1 X197.214 Y191.251 E.01604
G1 X188.749 Y182.786 E.35825
G1 X188.749 Y183.322 E.01604
G1 X196.678 Y191.251 E.33557
G1 X196.142 Y191.251 E.01604
G1 X188.749 Y183.858 E.31289
G1 X188.749 Y184.394 E.01604
G1 X195.606 Y191.251 E.29022
G1 X195.071 Y191.251 E.01604
G1 X188.749 Y184.929 E.26754
G1 X188.749 Y185.465 E.01604
G1 X194.535 Y191.251 E.24486
G1 X193.999 Y191.251 E.01604
G1 X188.749 Y186.001 E.22218
G1 X188.749 Y186.537 E.01604
G1 X193.463 Y191.251 E.19951
G1 X192.927 Y191.251 E.01604
G1 X188.749 Y187.073 E.17683
G1 X188.749 Y187.608 E.01604
G1 X192.392 Y191.251 E.15415
G1 X191.856 Y191.251 E.01604
G1 X188.749 Y188.144 E.13147
G1 X188.749 Y188.68 E.01604
G1 X191.32 Y191.251 E.10879
G1 X190.784 Y191.251 E.01604
G1 X188.749 Y189.216 E.08612
G1 X188.749 Y189.752 E.01604
G1 X190.248 Y191.251 E.06344
G1 X189.713 Y191.251 E.01604
G1 X188.749 Y190.287 E.04076
G1 X188.749 Y190.823 E.01604
G1 X189.346 Y191.42 E.02527
; WIPE_START
G1 X188.749 Y190.823 E-.3208
G1 X188.749 Y190.667 E-.0592
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.4 I1.157 J.377 P1  F60000
G1 X195.296 Y170.58 Z1.4
G1 Z1
G1 E.4 F1800
G1 F14252.909
M204 S8000
G1 X196.15 Y171.434 E.03613
G2 X195.462 Y171.282 I-1.157 J3.605 E.02111
G1 X194.93 Y170.749 E.02252
G1 X194.394 Y170.749 E.01604
G1 X194.895 Y171.25 E.0212
G2 X194.408 Y171.3 I.002 J2.458 E.01466
G1 X193.858 Y170.749 E.02328
G1 X193.323 Y170.749 E.01604
G1 X193.97 Y171.397 E.02742
G2 X193.574 Y171.536 I.497 J2.051 E.0126
G1 X192.787 Y170.749 E.03331
G1 X192.251 Y170.749 E.01604
G1 X193.209 Y171.707 E.04055
G2 X192.877 Y171.911 I.848 J1.759 E.01168
G1 X191.715 Y170.749 E.04916
G1 X191.179 Y170.749 E.01604
G1 X192.573 Y172.143 E.05898
G2 X192.297 Y172.403 I1.162 J1.513 E.01136
G1 X190.644 Y170.749 E.06997
G1 X190.108 Y170.749 E.01604
G1 X192.048 Y172.689 E.0821
G2 X191.826 Y173.004 I1.46 J1.264 E.01153
G1 X189.572 Y170.749 E.09541
G1 X189.036 Y170.749 E.01604
G1 X191.634 Y173.347 E.10994
G2 X191.48 Y173.729 I1.503 J.827 E.01236
G1 X188.749 Y170.999 E.11557
G1 X188.749 Y171.534 E.01604
G1 X191.353 Y174.138 E.11019
G2 X191.272 Y174.593 I2.231 J.631 E.01385
G1 X188.749 Y172.07 E.10677
G1 X188.749 Y172.606 E.01604
G1 X191.254 Y175.11 E.106
G2 X191.318 Y175.71 I3.029 J-.019 E.01808
G1 X188.749 Y173.142 E.1087
G1 X188.749 Y173.678 E.01604
G1 X191.556 Y176.484 E.11877
G2 X193.511 Y178.439 I3.426 J-1.471 E.08477
G1 X201.251 Y186.179 E.32759
G1 X201.251 Y185.643 E.01604
G1 X194.289 Y178.681 E.29466
G2 X194.889 Y178.745 I.746 J-4.121 E.01808
G1 X201.251 Y185.107 E.26925
G1 X201.251 Y184.571 E.01604
G1 X195.406 Y178.727 E.24735
G2 X195.864 Y178.649 I-.783 J-6.005 E.01391
G1 X201.251 Y184.035 E.22797
G1 X201.251 Y183.5 E.01604
G1 X196.274 Y178.523 E.21062
G2 X196.651 Y178.364 I-.606 J-1.962 E.01226
G1 X201.251 Y182.964 E.19467
G1 X201.251 Y182.428 E.01604
G1 X196.995 Y178.172 E.18013
G2 X197.309 Y177.951 I-.951 J-1.686 E.01153
G1 X201.251 Y181.892 E.16681
G1 X201.251 Y181.356 E.01604
G1 X197.596 Y177.702 E.15467
G2 X197.856 Y177.426 I-1.249 J-1.435 E.01136
G1 X201.251 Y180.821 E.14368
G1 X201.251 Y180.285 E.01604
G1 X198.088 Y177.122 E.13385
G2 X198.292 Y176.79 I-1.555 J-1.182 E.01168
G1 X201.251 Y179.749 E.12523
G1 X201.251 Y179.213 E.01604
G1 X198.46 Y176.422 E.11812
G2 X198.604 Y176.031 I-1.439 J-.752 E.01252
G1 X201.251 Y178.677 E.11201
G1 X201.251 Y178.142 E.01604
G1 X198.7 Y175.591 E.10794
G2 X198.747 Y175.102 I-2.425 J-.477 E.01474
G1 X201.251 Y177.606 E.10598
G1 X201.251 Y177.07 E.01604
G1 X198.72 Y174.539 E.10711
G2 X198.57 Y173.854 I-4.406 J.602 E.02101
G1 X201.251 Y176.534 E.11344
G1 X201.251 Y175.998 E.01604
G1 X196.002 Y170.749 E.22216
G1 X196.537 Y170.749 E.01604
G1 X201.251 Y175.463 E.19948
G1 X201.251 Y174.927 E.01604
G1 X197.073 Y170.749 E.1768
G1 X197.609 Y170.749 E.01604
G1 X201.251 Y174.391 E.15413
G1 X201.251 Y173.855 E.01604
G1 X198.145 Y170.749 E.13145
G1 X198.681 Y170.749 E.01604
G1 X201.251 Y173.319 E.10877
G1 X201.251 Y172.784 E.01604
G1 X199.216 Y170.749 E.08609
G1 X199.752 Y170.749 E.01604
G1 X201.251 Y172.248 E.06342
G1 X201.251 Y171.712 E.01604
G1 X200.288 Y170.749 E.04074
G1 X200.824 Y170.749 E.01604
G1 X201.42 Y171.346 E.02524
; OBJECT_ID: 12
; COOLING_NODE: 0
; WIPE_START
G1 X200.824 Y170.749 E-.3205
G1 X200.667 Y170.749 E-.0595
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 16
M625
; start printing object, unique label id: 12
M624 AgAAAAAAAAA=
M204 S10000
G17
G3 Z1.4 I1.215 J-.073 P1  F60000
G1 X197.447 Y117.382 Z1.4
G1 Z1
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X197.262 Y117.564 E.00833
G3 X194.745 Y111.593 I-2.254 J-2.566 E.41567
G1 X194.933 Y111.584 E.00605
G3 X197.507 Y117.326 I.076 J3.414 E.25732
M73 P35 R10
G1 X197.491 Y117.341 E.00072
; COOLING_NODE: 0
M204 S10000
G1 X197.163 Y117.091 F60000
G1 F13265.217
M204 S8000
G1 X196.992 Y117.257 E.00767
G3 X194.775 Y111.999 I-1.986 J-2.259 E.36621
G1 X194.938 Y111.991 E.00523
G3 X197.207 Y117.048 I.068 J3.007 E.22666
G1 X197.206 Y117.049 E.00006
; COOLING_NODE: 0
M204 S10000
G1 X196.878 Y116.799 F60000
G1 F13265.217
M204 S8000
G1 X196.722 Y116.951 E.00702
G3 X194.806 Y112.405 I-1.718 J-1.953 E.31674
G1 X194.943 Y112.398 E.00441
G3 X196.92 Y116.756 I.061 J2.6 E.1954
; COOLING_NODE: 0
M204 S250
G1 X196.605 Y116.517 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X196.289 Y116.793 E.0125
G3 X194.835 Y112.796 I-1.288 J-1.794 E.2427
G1 X194.948 Y112.791 E.00336
G3 X196.646 Y116.473 I.053 J2.208 E.15302
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X196.289 Y116.793 E-.1821
G1 X195.911 Y117.013 E-.16611
G1 X195.832 Y117.04 E-.03179
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.4 I-1.132 J.448 P1  F60000
G1 X201.584 Y131.584 Z1.4
G1 Z1
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y131.584 E.42342
G1 X188.416 Y110.416 E.68067
G1 X201.584 Y110.416 E.42342
G1 X201.584 Y131.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y131.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y131.991 E.4496
G1 X188.009 Y110.009 E.70685
G1 X201.991 Y110.009 E.4496
G1 X201.991 Y131.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y132.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y132.398 E.47578
G1 X187.602 Y109.602 E.73303
G1 X202.398 Y109.602 E.47578
G1 X202.398 Y132.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y132.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y132.79 E.46408
G1 X187.21 Y109.21 E.70237
G1 X202.79 Y109.21 E.46408
G1 X202.79 Y132.73 E.70058
; WIPE_START
M204 S8000
G1 X201.79 Y132.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.4 I1.215 J-.077 P1  F60000
G1 X201.42 Y126.884 Z1.4
G1 Z1
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42179
G1 F14252.909
M204 S8000
G1 X188.749 Y114.213 E.53628
G1 X188.749 Y114.749 E.01604
G1 X201.251 Y127.25 E.5291
G1 X201.251 Y127.786 E.01604
G1 X188.749 Y115.285 E.5291
G1 X188.749 Y115.821 E.01604
G1 X201.251 Y128.322 E.5291
G1 X201.251 Y128.858 E.01604
G1 X188.749 Y116.357 E.5291
G1 X188.749 Y116.892 E.01604
G1 X201.251 Y129.393 E.5291
G1 X201.251 Y129.929 E.01604
G1 X188.749 Y117.428 E.5291
G1 X188.749 Y117.964 E.01604
G1 X201.251 Y130.465 E.5291
G1 X201.251 Y131.001 E.01604
G1 X188.749 Y118.5 E.5291
G1 X188.749 Y119.036 E.01604
G1 X200.964 Y131.251 E.51699
G1 X200.429 Y131.251 E.01604
G1 X188.749 Y119.571 E.49431
G1 X188.749 Y120.107 E.01604
G1 X199.893 Y131.251 E.47164
G1 X199.357 Y131.251 E.01604
G1 X188.749 Y120.643 E.44896
G1 X188.749 Y121.179 E.01604
G1 X198.821 Y131.251 E.42628
G1 X198.285 Y131.251 E.01604
G1 X188.749 Y121.715 E.4036
G1 X188.749 Y122.25 E.01604
G1 X197.75 Y131.251 E.38093
G1 X197.214 Y131.251 E.01604
G1 X188.749 Y122.786 E.35825
G1 X188.749 Y123.322 E.01604
G1 X196.678 Y131.251 E.33557
G1 X196.142 Y131.251 E.01604
G1 X188.749 Y123.858 E.31289
G1 X188.749 Y124.394 E.01604
G1 X195.606 Y131.251 E.29022
G1 X195.071 Y131.251 E.01604
G1 X188.749 Y124.929 E.26754
G1 X188.749 Y125.465 E.01604
G1 X194.535 Y131.251 E.24486
G1 X193.999 Y131.251 E.01604
G1 X188.749 Y126.001 E.22218
G1 X188.749 Y126.537 E.01604
G1 X193.463 Y131.251 E.19951
G1 X192.927 Y131.251 E.01604
G1 X188.749 Y127.073 E.17683
G1 X188.749 Y127.608 E.01604
G1 X192.392 Y131.251 E.15415
G1 X191.856 Y131.251 E.01604
G1 X188.749 Y128.144 E.13147
G1 X188.749 Y128.68 E.01604
G1 X191.32 Y131.251 E.10879
G1 X190.784 Y131.251 E.01604
G1 X188.749 Y129.216 E.08612
G1 X188.749 Y129.752 E.01604
G1 X190.248 Y131.251 E.06344
G1 X189.713 Y131.251 E.01604
G1 X188.749 Y130.287 E.04076
G1 X188.749 Y130.823 E.01604
G1 X189.346 Y131.42 E.02527
; WIPE_START
G1 X188.749 Y130.823 E-.3208
G1 X188.749 Y130.667 E-.0592
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.4 I1.157 J.377 P1  F60000
G1 X195.296 Y110.58 Z1.4
G1 Z1
G1 E.4 F1800
G1 F14252.909
M204 S8000
G1 X196.15 Y111.434 E.03614
G2 X195.462 Y111.282 I-1.157 J3.605 E.02111
G1 X194.93 Y110.749 E.02252
G1 X194.394 Y110.749 E.01604
G1 X194.904 Y111.259 E.02158
G2 X194.414 Y111.305 I-.088 J1.707 E.01478
G1 X193.858 Y110.749 E.02351
G1 X193.323 Y110.749 E.01604
G1 X193.97 Y111.397 E.02742
G2 X193.572 Y111.535 I.49 J2.06 E.01263
G1 X192.787 Y110.749 E.03325
G1 X192.251 Y110.749 E.01604
G1 X193.209 Y111.707 E.04055
G2 X192.877 Y111.911 I.85 J1.763 E.01168
G1 X191.715 Y110.749 E.04916
G1 X191.179 Y110.749 E.01604
G1 X192.573 Y112.143 E.05898
G2 X192.297 Y112.403 I1.158 J1.509 E.01136
G1 X190.644 Y110.749 E.06997
G1 X190.108 Y110.749 E.01604
G1 X192.048 Y112.689 E.0821
G2 X191.826 Y113.004 I1.459 J1.263 E.01153
G1 X189.572 Y110.749 E.09541
G1 X189.036 Y110.749 E.01604
G1 X191.641 Y113.354 E.11023
G2 X191.476 Y113.726 I1.452 J.864 E.01219
G1 X188.749 Y110.999 E.11542
G1 X188.749 Y111.534 E.01604
G1 X191.353 Y114.138 E.11019
G2 X191.272 Y114.593 I2.233 J.632 E.01385
G1 X188.749 Y112.07 E.10677
G1 X188.749 Y112.606 E.01604
G1 X191.254 Y115.11 E.106
G2 X191.318 Y115.71 I3.027 J-.019 E.01808
G1 X188.749 Y113.142 E.1087
G1 X188.749 Y113.678 E.01604
G1 X191.556 Y116.484 E.11878
G2 X193.511 Y118.439 I3.415 J-1.461 E.08478
M73 P35 R9
G1 X201.251 Y126.179 E.32759
G1 X201.251 Y125.643 E.01604
G1 X194.289 Y118.681 E.29466
G2 X194.889 Y118.745 I.746 J-4.121 E.01808
G1 X201.251 Y125.107 E.26925
G1 X201.251 Y124.571 E.01604
G1 X195.406 Y118.727 E.24736
G2 X195.864 Y118.649 I-.783 J-6.003 E.01391
G1 X201.251 Y124.035 E.22797
G1 X201.251 Y123.5 E.01604
G1 X196.274 Y118.523 E.21062
G2 X196.651 Y118.364 I-.605 J-1.96 E.01226
G1 X201.251 Y122.964 E.19467
G1 X201.251 Y122.428 E.01604
G1 X196.995 Y118.172 E.18013
G2 X197.309 Y117.951 I-.948 J-1.683 E.01153
G1 X201.251 Y121.892 E.16681
G1 X201.251 Y121.356 E.01604
G1 X197.596 Y117.702 E.15467
G2 X197.856 Y117.426 I-1.25 J-1.435 E.01136
G1 X201.251 Y120.821 E.14368
G1 X201.251 Y120.285 E.01604
G1 X198.088 Y117.123 E.13384
G2 X198.286 Y116.784 I-1.33 J-1.003 E.01175
G1 X201.251 Y119.749 E.12548
G1 X201.251 Y119.213 E.01604
G1 X198.467 Y116.43 E.11781
G2 X198.604 Y116.031 I-1.925 J-.884 E.01264
G1 X201.251 Y118.677 E.11201
G1 X201.251 Y118.142 E.01604
G1 X198.7 Y115.591 E.10794
G2 X198.747 Y115.102 I-2.425 J-.477 E.01474
G1 X201.251 Y117.606 E.10598
G1 X201.251 Y117.07 E.01604
G1 X198.72 Y114.539 E.10711
G2 X198.57 Y113.854 I-4.413 J.604 E.02101
G1 X201.251 Y116.534 E.11344
G1 X201.251 Y115.998 E.01604
G1 X196.002 Y110.749 E.22216
G1 X196.537 Y110.749 E.01604
G1 X201.251 Y115.463 E.19948
G1 X201.251 Y114.927 E.01604
G1 X197.073 Y110.749 E.1768
G1 X197.609 Y110.749 E.01604
G1 X201.251 Y114.391 E.15413
G1 X201.251 Y113.855 E.01604
G1 X198.145 Y110.749 E.13145
G1 X198.681 Y110.749 E.01604
G1 X201.251 Y113.319 E.10877
G1 X201.251 Y112.784 E.01604
G1 X199.216 Y110.749 E.08609
G1 X199.752 Y110.749 E.01604
G1 X201.251 Y112.248 E.06342
G1 X201.251 Y111.712 E.01604
G1 X200.288 Y110.749 E.04074
G1 X200.824 Y110.749 E.01604
G1 X201.42 Y111.346 E.02524
; OBJECT_ID: 8
; COOLING_NODE: 0
; WIPE_START
G1 X200.824 Y110.749 E-.3205
G1 X200.667 Y110.749 E-.0595
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 12
M625
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z1.4 I-.102 J-1.213 P1  F60000
G1 X141.804 Y115.684 Z1.4
G1 Z1
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X141.804 Y174.884 E1.90366
G1 X140.196 Y174.884 E.05172
G1 X140.196 Y115.684 E1.90366
G1 X121.324 Y115.684 E.60686
G1 X121.324 Y113.516 E.0697
M73 P36 R9
G1 X157.584 Y113.516 E1.16599
G1 X157.584 Y115.684 E.0697
G1 X155.804 Y115.684 E.05723
G1 X155.804 Y174.884 E1.90366
G1 X154.196 Y174.884 E.05172
G1 X154.196 Y115.684 E1.90366
G1 X141.864 Y115.684 E.39654
; COOLING_NODE: 0
M204 S10000
G1 X142.211 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X142.211 Y175.291 E1.90366
G1 X141.255 Y175.291 E.03074
G1 X141.255 Y185.642 E.33287
G1 X141 Y185.866 E.01092
G1 X140.745 Y185.642 E.01092
G1 X140.745 Y175.291 E.33287
G1 X139.789 Y175.291 E.03074
G1 X139.789 Y116.091 E1.90366
G1 X120.917 Y116.091 E.60686
G1 X120.917 Y113.109 E.09588
G1 X157.991 Y113.109 E1.19217
G1 X157.991 Y116.091 E.09588
G1 X156.211 Y116.091 E.05723
G1 X156.211 Y175.291 E1.90366
G1 X155.255 Y175.291 E.03074
G1 X155.255 Y185.642 E.33287
G1 X155 Y185.866 E.01092
G1 X154.745 Y185.642 E.01092
G1 X154.745 Y175.291 E.33287
G1 X153.789 Y175.291 E.03074
G1 X153.789 Y116.091 E1.90366
G1 X142.271 Y116.091 E.37036
; COOLING_NODE: 0
M204 S10000
G1 X142.618 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X142.618 Y174.902 E1.87806
G1 X143.235 Y174.902 E.01982
G1 X143.235 Y175.698 E.02559
G1 X141.662 Y175.698 E.05055
G1 X141.662 Y185.827 E.32571
G1 X141.32 Y186.127 E.01465
G1 X141.32 Y186.98 E.02744
G3 X140.972 Y187.123 I-.388 J-.452 E.01229
G1 X140.922 Y187.108 E.00166
G3 X140.68 Y186.98 I.758 J-1.733 E.00881
G1 X140.68 Y186.127 E.02744
G1 X140.338 Y185.827 E.01465
G1 X140.338 Y175.698 E.32571
G1 X138.765 Y175.698 E.05055
G1 X138.765 Y174.902 E.02559
G1 X139.382 Y174.902 E.01982
G1 X139.382 Y116.498 E1.87806
G1 X120.51 Y116.498 E.60686
G1 X120.51 Y112.702 E.12206
G1 X158.398 Y112.702 E1.21835
G1 X158.398 Y116.498 E.12206
G1 X156.618 Y116.498 E.05723
G1 X156.618 Y174.902 E1.87806
G1 X157.235 Y174.902 E.01982
G1 X157.235 Y175.698 E.02559
G1 X155.662 Y175.698 E.05055
G1 X155.662 Y185.827 E.32571
G1 X155.32 Y186.127 E.01465
G1 X155.32 Y186.48 E.01136
G3 X154.972 Y186.623 I-.388 J-.452 E.01229
G1 X154.922 Y186.608 E.00167
G3 X154.68 Y186.48 I.759 J-1.734 E.00881
G1 X154.68 Y186.127 E.01136
G1 X154.338 Y185.827 E.01465
G1 X154.338 Y175.698 E.32571
G1 X152.765 Y175.698 E.05055
G1 X152.765 Y174.902 E.02559
G1 X153.382 Y174.902 E.01982
G1 X153.382 Y116.498 E1.87806
G1 X142.678 Y116.498 E.34418
; COOLING_NODE: 0
M204 S250
G1 X143.01 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F3572
M204 S5000
G1 X143.01 Y174.51 E1.7163
G1 X143.627 Y174.51 E.01835
G1 X143.627 Y176.09 E.04706
G1 X142.055 Y176.09 E.04683
G1 X142.055 Y186.005 E.29533
G1 X141.712 Y186.305 E.01357
G1 X141.712 Y187.189 E.02634
G3 X141.021 Y187.518 I-.976 J-1.16 E.02305
G3 X140.446 Y187.297 I.052 J-.993 E.01866
G1 X140.288 Y187.189 E.00568
G1 X140.288 Y186.305 E.02634
G1 X139.945 Y186.005 E.01357
G1 X139.945 Y176.09 E.29533
G1 X138.373 Y176.09 E.04683
G1 X138.373 Y174.51 E.04706
G1 X138.99 Y174.51 E.01835
G1 X138.99 Y116.89 E1.7163
G1 X120.128 Y116.89 E.56181
G1 X120.118 Y116.89 E.00032
G1 X120.118 Y112.31 E.13642
G1 X120.128 Y112.31 E.00032
G1 X158.79 Y112.31 E1.1516
G1 X158.79 Y116.89 E.13642
G1 X157.01 Y116.89 E.05301
G1 X157.01 Y174.51 E1.7163
M73 P37 R9
G1 X157.627 Y174.51 E.01835
G1 X157.627 Y176.09 E.04706
G1 X156.055 Y176.09 E.04683
G1 X156.055 Y186.005 E.29533
G1 X155.712 Y186.305 E.01357
G1 X155.712 Y186.689 E.01144
G3 X155.021 Y187.018 I-.976 J-1.16 E.02305
G3 X154.445 Y186.796 I.052 J-.993 E.01867
G1 X154.288 Y186.689 E.00567
G1 X154.288 Y186.305 E.01144
G1 X153.945 Y186.005 E.01357
G1 X153.945 Y176.09 E.29533
G1 X152.373 Y176.09 E.04683
G1 X152.373 Y174.51 E.04706
G1 X152.99 Y174.51 E.01835
G1 X152.99 Y116.89 E1.7163
G1 X143.07 Y116.89 E.29546
; WIPE_START
G1 F12000
M204 S8000
G1 X143.069 Y117.89 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.4 I-1.216 J-.044 P1  F60000
G1 X141 Y175.087 Z1.4
G1 Z1
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.14662
G1 F15000
M204 S8000
G1 X141 Y185.595 E.08608
M204 S10000
G1 X141.116 Y186.093 F60000
; LINE_WIDTH: 0.206135
G1 F15000
M204 S8000
G1 X141.058 Y186.173 E.00127
; LINE_WIDTH: 0.252285
G1 X141 Y186.253 E.00164
; LINE_WIDTH: 0.275358
G1 X141 Y186.791 E.00988
G1 X141.052 Y186.895 E.00213
; WIPE_START
G1 X141 Y186.791 E-.06751
G1 X141 Y186.253 E-.31249
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.4 I.057 J1.216 P1  F60000
G1 X155 Y185.595 Z1.4
G1 Z1
G1 E.4 F1800
; LINE_WIDTH: 0.14662
G1 F15000
M204 S8000
G1 X155 Y175.087 E.08608
; WIPE_START
G1 X155 Y176.087 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.4 I1.217 J0 P1  F60000
G1 X155 Y174.08 Z1.4
G1 Z1
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.49002
G1 F12077.835
M204 S8000
G1 X155 Y115.54 E2.06748
; WIPE_START
G1 X155 Y116.54 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.4 I-1.182 J-.288 P1  F60000
G1 X141 Y174.08 Z1.4
G1 Z1
G1 E.4 F1800
G1 F12077.835
M204 S8000
G1 X141 Y115.54 E2.06748
; WIPE_START
G1 X141 Y116.54 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.4 I-1.217 J-.009 P1  F60000
G1 X140.588 Y174.492 Z1.4
G1 Z1
G1 E.4 F1800
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X141.412 Y174.492 E.02455
G1 X141.412 Y115.48 E1.75771
G1 X141.485 Y115.331 E.00495
G1 X141.601 Y115.292 E.00363
G1 X154.399 Y115.292 E.38122
G1 X154.558 Y115.378 E.00537
G1 X154.588 Y115.48 E.00318
G1 X154.588 Y174.492 E1.75771
G1 X155.412 Y174.492 E.02455
G1 X155.412 Y115.48 E1.75771
G1 X155.485 Y115.331 E.00495
G1 X155.601 Y115.292 E.00363
G1 X157.192 Y115.292 E.04739
G1 X157.192 Y113.908 E.04121
G1 X121.716 Y113.908 E1.05668
G1 X121.716 Y115.292 E.04121
G1 X140.399 Y115.292 E.5565
G1 X140.558 Y115.378 E.00537
G1 X140.588 Y115.48 E.00318
G1 X140.588 Y174.432 E1.75592
; WIPE_START
G1 X140.588 Y173.432 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.4 I1.217 J.009 P1  F60000
G1 X141 Y115.48 Z1.4
G1 Z1
G1 E.4 F1800
; LINE_WIDTH: 0.472998
G1 F12555.877
M204 S8000
G1 X141.063 Y115.326 E.00565
; LINE_WIDTH: 0.438953
G1 F13635.244
G1 X141.125 Y115.172 E.0052
; LINE_WIDTH: 0.44374
G1 F13472.382
G1 X141.247 Y115.067 E.0051
; LINE_WIDTH: 0.48736
G1 F12150.122
G1 X141.369 Y114.963 E.00565
; LINE_WIDTH: 0.545962
G1 F10734.702
G1 X141.491 Y114.858 E.0064
G1 X141.601 Y114.852 E.00435
G1 X154.399 Y114.852 E.50858
; LINE_WIDTH: 0.525099
G1 F11199.176
G1 X154.515 Y114.912 E.00495
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X154.63 Y114.972 E.00452
; LINE_WIDTH: 0.429089
G1 F13983.535
G3 X154.875 Y115.172 I-.161 J.447 E.00984
; LINE_WIDTH: 0.438953
G1 F13635.244
G1 X154.937 Y115.326 E.0052
; LINE_WIDTH: 0.461649
G1 F12896.166
G1 X155 Y115.48 E.0055
G1 X155.125 Y115.172 E.01099
; LINE_WIDTH: 0.44374
G1 F13472.382
G1 X155.247 Y115.067 E.0051
; LINE_WIDTH: 0.48736
G1 F12150.122
G1 X155.369 Y114.963 E.00565
; LINE_WIDTH: 0.546422
G1 F10724.898
G1 X155.491 Y114.858 E.0064
G3 X156.752 Y114.852 I1.134 J103.16 E.05012
G1 X156.752 Y114.348 E.02001
G1 X155.601 Y114.348 E.04578
; LINE_WIDTH: 0.525099
G1 F11199.176
G1 X155.4 Y114.327 E.00767
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X155.2 Y114.306 E.007
; LINE_WIDTH: 0.441012
G1 F13564.713
G1 X155 Y114.285 E.00633
G1 X154.8 Y114.306 E.00633
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X154.6 Y114.327 E.007
; LINE_WIDTH: 0.545795
G1 F10738.267
G1 X154.399 Y114.348 E.008
G1 X141.601 Y114.348 E.50841
; LINE_WIDTH: 0.525099
G1 F11199.176
G1 X141.4 Y114.327 E.00767
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X141.2 Y114.306 E.007
; LINE_WIDTH: 0.441012
G1 F13564.713
G1 X141 Y114.285 E.00633
G1 X140.8 Y114.306 E.00633
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X140.6 Y114.327 E.007
; LINE_WIDTH: 0.546007
G1 F10733.747
G1 X140.399 Y114.348 E.008
G1 X122.156 Y114.348 E.725
G1 X122.156 Y114.852 E.02
G1 X140.399 Y114.852 E.725
; LINE_WIDTH: 0.525099
G1 F11199.176
G1 X140.515 Y114.912 E.00495
; LINE_WIDTH: 0.483055
G1 F12268.962
G1 X140.63 Y114.972 E.00452
; LINE_WIDTH: 0.429089
G1 F13983.535
G3 X140.875 Y115.172 I-.161 J.447 E.00984
; LINE_WIDTH: 0.438953
G1 F13635.244
G1 X140.926 Y115.298 E.00426
; LINE_WIDTH: 0.472998
G1 F12555.877
G1 X140.977 Y115.425 E.00463
M204 S10000
G1 X141.029 Y114.653 F60000
; LINE_WIDTH: 0.50008
G1 F11812.057
M204 S8000
G2 X141.026 Y114.752 I-.029 J.049 E.00845
; WIPE_START
G1 X140.971 Y114.752 E-.09138
G1 X140.943 Y114.702 E-.0962
G1 X140.971 Y114.653 E-.0962
G1 X141.029 Y114.653 E-.09621
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.4 I0 J1.217 P1  F60000
G1 X155.029 Y114.653 Z1.4
G1 Z1
G1 E.4 F1800
G1 F11812.057
M204 S8000
G2 X155.026 Y114.752 I-.029 J.049 E.00845
; COOLING_NODE: 0
; WIPE_START
G1 X154.971 Y114.752 E-.09138
G1 X154.943 Y114.702 E-.0962
G1 X154.971 Y114.653 E-.0962
G1 X155.029 Y114.653 E-.09621
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.4 I-.031 J-1.217 P1  F60000
G1 X114.676 Y115.684 Z1.4
G1 Z1
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X112.416 Y115.684 E.07267
G1 X112.416 Y113.516 E.0697
G1 X114.676 Y113.516 E.07267
G1 X114.676 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X115.083 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X112.009 Y116.091 E.09885
G1 X112.009 Y113.109 E.09588
G1 X115.083 Y113.109 E.09885
G1 X115.083 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X115.49 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X111.602 Y116.498 E.12503
G1 X111.602 Y112.702 E.12206
G1 X115.49 Y112.702 E.12503
G1 X115.49 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X115.872 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F3572
M204 S5000
G1 X111.21 Y116.89 E.13885
G1 X111.21 Y112.31 E.13642
G1 X115.872 Y112.31 E.13885
G1 X115.882 Y112.31 E.00032
G1 X115.882 Y116.841 E.13496
; WIPE_START
G1 F12000
M204 S8000
G1 X114.882 Y116.851 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.4 I1.136 J-.436 P1  F60000
G1 X114.284 Y115.292 Z1.4
G1 Z1
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X114.284 Y113.908 E.04121
G1 X112.808 Y113.908 E.04396
G1 X112.808 Y115.292 E.04121
G1 X114.224 Y115.292 E.04217
M204 S10000
G1 X113.844 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X113.844 Y114.348 E.02
G1 X113.248 Y114.348 E.02367
G1 X113.248 Y114.852 E.02
G1 X113.784 Y114.852 E.02129
; CHANGE_LAYER
; Z_HEIGHT: 1.2
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F10731.32
G1 X113.248 Y114.852 E-.20353
G1 X113.248 Y114.387 E-.17647
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 6/27
; update layer progress
M73 L6
M991 S0 P5 ;notify layer change
; OBJECT_ID: 16
; COOLING_NODE: 0
; start printing object, unique label id: 16
M624 BAAAAAAAAAA=
M204 S10000
G17
G3 Z1.4 I-.75 J.958 P1  F60000
G1 X195.055 Y178.408 Z1.4
G1 Z1.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X194.745 Y178.398 E.00996
G3 X194.575 Y171.609 I.254 J-3.403 E.3229
G1 X194.915 Y171.583 E.01096
G3 X195.255 Y178.398 I.085 J3.412 E.3393
M73 P38 R9
G1 X195.115 Y178.405 E.0045
; COOLING_NODE: 0
M204 S10000
G1 X195.053 Y178.001 F60000
G1 F13265.217
M204 S8000
G1 X194.776 Y177.993 E.00893
G3 X194.626 Y172.013 I.224 J-2.998 E.2844
G1 X194.925 Y171.991 E.00965
G3 X195.224 Y177.993 I.075 J3.005 E.29885
G1 X195.113 Y177.999 E.00357
; COOLING_NODE: 0
M204 S10000
G1 X195.052 Y177.595 F60000
G1 F13265.217
M204 S8000
G1 X194.806 Y177.588 E.00792
G3 X194.676 Y172.417 I.194 J-2.592 E.2459
G1 X194.935 Y172.398 E.00835
G3 X195.194 Y177.588 I.065 J2.598 E.25839
G1 X195.112 Y177.592 E.00263
; COOLING_NODE: 0
M204 S250
G1 X195.052 Y177.204 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X194.835 Y177.198 E.00645
G3 X194.725 Y172.807 I.164 J-2.201 E.19343
G1 X194.945 Y172.79 E.00657
G3 X195.165 Y177.198 I.055 J2.206 E.20326
G1 X195.112 Y177.201 E.00158
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X194.835 Y177.198 E-.10501
G1 X194.401 Y177.128 E-.16707
G1 X194.137 Y177.024 E-.10791
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.6 I-1.083 J.554 P1  F60000
G1 X201.584 Y191.584 Z1.6
G1 Z1.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y191.584 E.42342
G1 X188.416 Y170.416 E.68067
G1 X201.584 Y170.416 E.42342
G1 X201.584 Y191.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y191.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y191.991 E.4496
G1 X188.009 Y170.009 E.70685
G1 X201.991 Y170.009 E.4496
G1 X201.991 Y191.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y192.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y192.398 E.47578
G1 X187.602 Y169.602 E.73303
G1 X202.398 Y169.602 E.47578
G1 X202.398 Y192.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y192.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y192.79 E.46408
G1 X187.21 Y169.21 E.70237
G1 X202.79 Y169.21 E.46408
G1 X202.79 Y192.73 E.70058
; object ids of layer 6 start: 8,12,16
M624 BwAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer6 end: 8,12,16
M625
; WIPE_START
M204 S8000
G1 X201.79 Y192.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.6 I.921 J-.796 P1  F60000
G1 X200.654 Y191.42 Z1.6
G1 Z1.2
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42179
G1 F14252.909
M204 S8000
G1 X201.251 Y190.824 E.02524
G1 X201.251 Y190.288 E.01604
G1 X200.288 Y191.251 E.04074
G1 X199.752 Y191.251 E.01604
G1 X201.251 Y189.752 E.06342
G1 X201.251 Y189.216 E.01604
G1 X199.216 Y191.251 E.08609
G1 X198.681 Y191.251 E.01604
G1 X201.251 Y188.681 E.10877
G1 X201.251 Y188.145 E.01604
G1 X198.145 Y191.251 E.13145
G1 X197.609 Y191.251 E.01604
G1 X201.251 Y187.609 E.15413
G1 X201.251 Y187.073 E.01604
G1 X197.073 Y191.251 E.1768
G1 X196.537 Y191.251 E.01604
G1 X201.251 Y186.537 E.19948
G1 X201.251 Y186.002 E.01604
G1 X196.002 Y191.251 E.22216
G1 X195.466 Y191.251 E.01604
G1 X201.251 Y185.466 E.24484
G1 X201.251 Y184.93 E.01604
G1 X194.93 Y191.251 E.26751
G1 X194.394 Y191.251 E.01604
G1 X201.251 Y184.394 E.29019
G1 X201.251 Y183.858 E.01604
G1 X193.858 Y191.251 E.31287
G1 X193.323 Y191.251 E.01604
G1 X201.251 Y183.323 E.33555
G1 X201.251 Y182.787 E.01604
G1 X192.787 Y191.251 E.35823
G1 X192.251 Y191.251 E.01604
G1 X201.251 Y182.251 E.3809
G1 X201.251 Y181.715 E.01604
G1 X191.715 Y191.251 E.40358
G1 X191.179 Y191.251 E.01604
G1 X201.251 Y181.179 E.42626
G1 X201.251 Y180.644 E.01604
G1 X190.644 Y191.251 E.44894
G1 X190.108 Y191.251 E.01604
G1 X201.251 Y180.108 E.47161
G1 X201.251 Y179.572 E.01604
G1 X189.572 Y191.251 E.49429
G1 X189.036 Y191.251 E.01604
G1 X201.251 Y179.036 E.51697
G1 X201.251 Y178.5 E.01604
G1 X188.749 Y191.001 E.5291
G1 X188.749 Y190.466 E.01604
G1 X201.251 Y177.965 E.5291
G1 X201.251 Y177.429 E.01604
G1 X188.749 Y189.93 E.5291
G1 X188.749 Y189.394 E.01604
G1 X201.251 Y176.893 E.5291
G1 X201.251 Y176.357 E.01604
G1 X188.749 Y188.858 E.5291
G1 X188.749 Y188.322 E.01604
G1 X201.251 Y175.821 E.5291
G1 X201.251 Y175.286 E.01604
G1 X188.749 Y187.787 E.5291
G1 X188.749 Y187.251 E.01604
G1 X201.251 Y174.75 E.5291
G1 X201.251 Y174.214 E.01604
G1 X188.749 Y186.715 E.5291
G1 X188.749 Y186.179 E.01604
G1 X196.487 Y178.442 E.32749
G3 X195.714 Y178.679 I-1.545 J-3.656 E.02425
G1 X188.749 Y185.643 E.29477
G1 X188.749 Y185.108 E.01604
G1 X195.11 Y178.748 E.26919
G3 X194.596 Y178.726 I-.066 J-4.499 E.0154
G1 X188.749 Y184.572 E.24744
G1 X188.749 Y184.036 E.01604
G1 X194.139 Y178.647 E.2281
G3 X193.725 Y178.525 I.404 J-2.127 E.01293
G1 X188.749 Y183.5 E.21059
G1 X188.749 Y182.964 E.01604
G1 X193.348 Y178.365 E.19465
G3 X193.005 Y178.173 I.792 J-1.813 E.0118
G1 X188.749 Y182.429 E.18012
G1 X188.749 Y181.893 E.01604
G1 X192.689 Y177.953 E.16674
G3 X192.402 Y177.705 I1.098 J-1.557 E.01139
G1 X188.749 Y181.357 E.15459
G1 X188.749 Y180.821 E.01604
G1 X192.143 Y177.427 E.14364
G3 X191.909 Y177.125 I1.391 J-1.319 E.01145
G1 X188.749 Y180.285 E.13374
G1 X188.749 Y179.75 E.01604
G1 X191.705 Y176.794 E.1251
G3 X191.533 Y176.43 I1.734 J-1.042 E.01206
G1 X188.749 Y179.214 E.11782
G1 X188.749 Y178.678 E.01604
G1 X191.396 Y176.031 E.11202
G3 X191.3 Y175.592 I2.15 J-.701 E.01349
G1 X188.749 Y178.142 E.10795
G1 X188.749 Y177.606 E.01604
G1 X191.253 Y175.102 E.10598
G3 X191.28 Y174.54 I4.2 J-.083 E.01686
G1 X188.749 Y177.071 E.10711
G1 X188.749 Y176.535 E.01604
G1 X191.722 Y173.562 E.1258
; WIPE_START
G1 X191.015 Y174.27 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.6 I1.109 J-.501 P1  F60000
G1 X189.346 Y170.58 Z1.6
G1 Z1.2
G1 E.4 F1800
G1 F14252.909
M204 S8000
G1 X188.749 Y171.177 E.02527
G1 X188.749 Y171.713 E.01604
G1 X189.713 Y170.749 E.04076
G1 X190.248 Y170.749 E.01604
G1 X188.749 Y172.248 E.06344
G1 X188.749 Y172.784 E.01604
G1 X190.784 Y170.749 E.08612
G1 X191.32 Y170.749 E.01604
G1 X188.749 Y173.32 E.10879
G1 X188.749 Y173.856 E.01604
G1 X191.856 Y170.749 E.13147
G1 X192.392 Y170.749 E.01604
G1 X188.749 Y174.392 E.15415
G1 X188.749 Y174.927 E.01604
G1 X192.927 Y170.749 E.17683
G1 X193.463 Y170.749 E.01604
G1 X188.749 Y175.463 E.19951
G1 X188.749 Y175.999 E.01604
G1 X193.999 Y170.749 E.22218
G1 X194.535 Y170.749 E.01604
G1 X193.854 Y171.43 E.0288
G3 X194.543 Y171.277 I1.466 J4.969 E.02114
G1 X195.071 Y170.749 E.02232
G1 X195.606 Y170.749 E.01604
G1 X195.101 Y171.254 E.02137
G3 X195.594 Y171.298 I.028 J2.48 E.01481
G1 X196.142 Y170.749 E.02322
G1 X196.678 Y170.749 E.01604
G1 X196.033 Y171.394 E.02729
G3 X196.429 Y171.534 I-.499 J2.044 E.01259
G1 X197.214 Y170.749 E.03321
G1 X197.75 Y170.749 E.01604
G1 X196.791 Y171.708 E.04056
G3 X197.123 Y171.912 I-.853 J1.759 E.01168
G1 X198.285 Y170.749 E.04919
G1 X198.821 Y170.749 E.01604
G1 X197.427 Y172.144 E.05903
G3 X197.703 Y172.404 I-1.163 J1.512 E.01136
G1 X199.357 Y170.749 E.07002
G1 X199.893 Y170.749 E.01604
G1 X197.951 Y172.691 E.08217
G3 X198.172 Y173.006 I-1.464 J1.263 E.01153
G1 X200.429 Y170.749 E.09549
G1 X200.964 Y170.749 E.01604
G1 X198.364 Y173.35 E.11006
G3 X198.524 Y173.726 I-1.801 J.986 E.01225
G1 X201.251 Y170.999 E.11541
G1 X201.251 Y171.535 E.01604
G1 X198.647 Y174.138 E.11019
G3 X198.728 Y174.593 I-2.234 J.632 E.01385
G1 X201.251 Y172.071 E.10677
G1 X201.251 Y172.607 E.01604
G1 X198.746 Y175.111 E.106
G3 X198.682 Y175.711 I-3.028 J-.02 E.01808
G1 X201.251 Y173.142 E.10871
G1 X201.251 Y173.678 E.01604
G1 X198.035 Y176.893 E.13608
; OBJECT_ID: 12
; COOLING_NODE: 0
; WIPE_START
G1 X198.743 Y176.186 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 16
M625
; start printing object, unique label id: 12
M624 AgAAAAAAAAA=
M204 S10000
G17
G3 Z1.6 I1.217 J-.026 P1  F60000
G1 X197.498 Y117.329 Z1.6
G1 Z1.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X197.463 Y117.374 E.00182
G3 X194.744 Y111.593 I-2.454 J-2.376 E.4246
G1 X194.933 Y111.584 E.00606
G3 X197.626 Y117.193 I.076 J3.415 E.2516
G1 X197.539 Y117.285 E.00411
; COOLING_NODE: 0
M204 S10000
G1 X197.219 Y117.024 F60000
G1 F13265.217
M204 S8000
G1 X197.169 Y117.089 E.00265
G3 X194.775 Y111.999 I-2.163 J-2.091 E.37409
G1 X194.938 Y111.991 E.00524
G3 X197.489 Y116.697 I.069 J3.008 E.2122
G1 X197.257 Y116.978 E.01171
; COOLING_NODE: 0
M204 S10000
G1 X196.905 Y116.767 F60000
G1 F13265.217
M204 S8000
G1 X196.875 Y116.805 E.00154
G3 X194.805 Y112.405 I-1.872 J-1.806 E.32358
G1 X194.943 Y112.398 E.00442
G3 X197.151 Y116.466 I.061 J2.6 E.18349
G1 X196.943 Y116.721 E.01056
; COOLING_NODE: 0
M204 S250
G1 X196.602 Y116.52 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X196.593 Y116.531 E.00043
G3 X194.835 Y112.796 I-1.591 J-1.532 E.25467
G1 X194.948 Y112.79 E.00336
G3 X196.825 Y116.244 I.054 J2.208 E.14437
G1 X196.64 Y116.473 E.00877
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X196.593 Y116.531 E-.02828
M73 P39 R9
G1 X196.29 Y116.795 E-.15256
G1 X195.909 Y117.015 E-.16725
G1 X195.829 Y117.041 E-.03192
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.6 I-1.132 J.448 P1  F60000
G1 X201.584 Y131.584 Z1.6
G1 Z1.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y131.584 E.42342
G1 X188.416 Y110.416 E.68067
G1 X201.584 Y110.416 E.42342
G1 X201.584 Y131.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y131.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y131.991 E.4496
G1 X188.009 Y110.009 E.70685
G1 X201.991 Y110.009 E.4496
G1 X201.991 Y131.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y132.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y132.398 E.47578
G1 X187.602 Y109.602 E.73303
G1 X202.398 Y109.602 E.47578
G1 X202.398 Y132.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y132.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y132.79 E.46408
G1 X187.21 Y109.21 E.70237
G1 X202.79 Y109.21 E.46408
G1 X202.79 Y132.73 E.70058
; WIPE_START
M204 S8000
G1 X201.79 Y132.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.6 I.921 J-.796 P1  F60000
G1 X200.654 Y131.42 Z1.6
G1 Z1.2
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42179
G1 F14252.909
M204 S8000
G1 X201.251 Y130.824 E.02524
G1 X201.251 Y130.288 E.01604
G1 X200.288 Y131.251 E.04074
G1 X199.752 Y131.251 E.01604
G1 X201.251 Y129.752 E.06342
G1 X201.251 Y129.216 E.01604
G1 X199.216 Y131.251 E.08609
G1 X198.681 Y131.251 E.01604
G1 X201.251 Y128.681 E.10877
G1 X201.251 Y128.145 E.01604
G1 X198.145 Y131.251 E.13145
G1 X197.609 Y131.251 E.01604
G1 X201.251 Y127.609 E.15413
G1 X201.251 Y127.073 E.01604
G1 X197.073 Y131.251 E.1768
G1 X196.537 Y131.251 E.01604
G1 X201.251 Y126.537 E.19948
G1 X201.251 Y126.002 E.01604
G1 X196.002 Y131.251 E.22216
G1 X195.466 Y131.251 E.01604
G1 X201.251 Y125.466 E.24484
G1 X201.251 Y124.93 E.01604
G1 X194.93 Y131.251 E.26751
G1 X194.394 Y131.251 E.01604
G1 X201.251 Y124.394 E.29019
G1 X201.251 Y123.858 E.01604
G1 X193.858 Y131.251 E.31287
G1 X193.323 Y131.251 E.01604
G1 X201.251 Y123.323 E.33555
G1 X201.251 Y122.787 E.01604
G1 X192.787 Y131.251 E.35823
G1 X192.251 Y131.251 E.01604
G1 X201.251 Y122.251 E.3809
G1 X201.251 Y121.715 E.01604
G1 X191.715 Y131.251 E.40358
G1 X191.179 Y131.251 E.01604
G1 X201.251 Y121.179 E.42626
G1 X201.251 Y120.644 E.01604
G1 X190.644 Y131.251 E.44894
G1 X190.108 Y131.251 E.01604
G1 X201.251 Y120.108 E.47161
G1 X201.251 Y119.572 E.01604
G1 X189.572 Y131.251 E.49429
G1 X189.036 Y131.251 E.01604
G1 X201.251 Y119.036 E.51697
G1 X201.251 Y118.5 E.01604
G1 X188.749 Y131.001 E.5291
G1 X188.749 Y130.466 E.01604
G1 X201.251 Y117.965 E.5291
G1 X201.251 Y117.429 E.01604
G1 X188.749 Y129.93 E.5291
G1 X188.749 Y129.394 E.01604
G1 X201.251 Y116.893 E.5291
G1 X201.251 Y116.357 E.01604
G1 X188.749 Y128.858 E.5291
G1 X188.749 Y128.322 E.01604
G1 X201.251 Y115.821 E.5291
G1 X201.251 Y115.286 E.01604
G1 X188.749 Y127.787 E.5291
G1 X188.749 Y127.251 E.01604
G1 X201.251 Y114.75 E.5291
G1 X201.251 Y114.214 E.01604
G1 X188.749 Y126.715 E.5291
G1 X188.749 Y126.179 E.01604
G1 X196.487 Y118.442 E.32749
G3 X195.714 Y118.679 I-1.546 J-3.657 E.02425
G1 X188.749 Y125.643 E.29477
G1 X188.749 Y125.108 E.01604
G1 X195.108 Y118.749 E.26911
G3 X194.596 Y118.726 I-.003 J-5.451 E.01534
G1 X188.749 Y124.572 E.24744
G1 X188.749 Y124.036 E.01604
G1 X194.139 Y118.647 E.2281
G3 X193.725 Y118.524 I.404 J-2.127 E.01293
G1 X188.749 Y123.5 E.21059
G1 X188.749 Y122.964 E.01604
G1 X193.348 Y118.366 E.19465
G3 X193.004 Y118.174 I.784 J-1.818 E.01181
G1 X188.749 Y122.429 E.18007
G1 X188.749 Y121.893 E.01604
G1 X192.689 Y117.953 E.16674
G3 X192.402 Y117.705 I1.101 J-1.561 E.01139
G1 X188.749 Y121.357 E.15459
G1 X188.749 Y120.821 E.01604
G1 X192.142 Y117.429 E.14359
G3 X191.909 Y117.125 I1.394 J-1.31 E.01146
G1 X188.749 Y120.285 E.13374
G1 X188.749 Y119.75 E.01604
G1 X191.705 Y116.794 E.1251
G3 X191.533 Y116.43 I1.731 J-1.041 E.01206
G1 X188.749 Y119.214 E.11782
G1 X188.749 Y118.678 E.01604
G1 X191.396 Y116.031 E.11202
G3 X191.3 Y115.592 I2.154 J-.702 E.01349
G1 X188.749 Y118.142 E.10795
G1 X188.749 Y117.606 E.01604
G1 X191.253 Y115.102 E.10598
G3 X191.28 Y114.54 I4.193 J-.083 E.01686
G1 X188.749 Y117.071 E.10711
G1 X188.749 Y116.535 E.01604
G1 X191.722 Y113.562 E.1258
; WIPE_START
G1 X191.015 Y114.27 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.6 I1.109 J-.501 P1  F60000
G1 X189.346 Y110.58 Z1.6
G1 Z1.2
G1 E.4 F1800
G1 F14252.909
M204 S8000
G1 X188.749 Y111.177 E.02527
G1 X188.749 Y111.713 E.01604
G1 X189.713 Y110.749 E.04076
G1 X190.248 Y110.749 E.01604
G1 X188.749 Y112.248 E.06344
G1 X188.749 Y112.784 E.01604
G1 X190.784 Y110.749 E.08612
G1 X191.32 Y110.749 E.01604
G1 X188.749 Y113.32 E.10879
G1 X188.749 Y113.856 E.01604
G1 X191.856 Y110.749 E.13147
G1 X192.392 Y110.749 E.01604
G1 X188.749 Y114.392 E.15415
G1 X188.749 Y114.927 E.01604
G1 X192.927 Y110.749 E.17683
G1 X193.463 Y110.749 E.01604
G1 X188.749 Y115.463 E.19951
G1 X188.749 Y115.999 E.01604
G1 X193.999 Y110.749 E.22218
G1 X194.535 Y110.749 E.01604
G1 X193.854 Y111.43 E.0288
G3 X194.533 Y111.287 I.896 J2.579 E.0208
G1 X195.071 Y110.749 E.02277
G1 X195.606 Y110.749 E.01604
G1 X195.097 Y111.259 E.02155
G3 X195.594 Y111.298 I.094 J1.96 E.01494
G1 X196.142 Y110.749 E.02322
G1 X196.678 Y110.749 E.01604
G1 X196.033 Y111.394 E.02729
G3 X196.429 Y111.534 I-.502 J2.052 E.01259
G1 X197.214 Y110.749 E.03321
G1 X197.75 Y110.749 E.01604
G1 X196.791 Y111.708 E.04055
G3 X197.123 Y111.912 I-.852 J1.758 E.01168
G1 X198.285 Y110.749 E.04919
G1 X198.821 Y110.749 E.01604
G1 X197.427 Y112.144 E.05903
G3 X197.703 Y112.404 I-1.161 J1.51 E.01136
G1 X199.357 Y110.749 E.07002
G1 X199.893 Y110.749 E.01604
G1 X197.951 Y112.691 E.08217
G3 X198.172 Y113.006 I-1.46 J1.26 E.01153
G1 X200.429 Y110.749 E.09549
G1 X200.964 Y110.749 E.01604
G1 X198.364 Y113.35 E.11006
G3 X198.524 Y113.726 I-1.8 J.986 E.01225
G1 X201.251 Y110.999 E.11541
G1 X201.251 Y111.535 E.01604
G1 X198.647 Y114.138 E.11019
G3 X198.728 Y114.593 I-2.235 J.632 E.01385
G1 X201.251 Y112.071 E.10677
G1 X201.251 Y112.607 E.01604
G1 X198.746 Y115.111 E.106
G3 X198.682 Y115.711 I-3.029 J-.02 E.01808
G1 X201.251 Y113.142 E.10871
G1 X201.251 Y113.678 E.01604
G1 X198.035 Y116.893 E.13608
; OBJECT_ID: 8
; COOLING_NODE: 0
; WIPE_START
G1 X198.743 Y116.186 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 12
M625
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z1.6 I.011 J-1.217 P1  F60000
G1 X141.74 Y115.684 Z1.6
G1 Z1.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X141.74 Y174.884 E1.90366
G1 X140.26 Y174.884 E.04758
G1 X140.26 Y115.684 E1.90366
G1 X121.249 Y115.684 E.61134
G1 X121.249 Y113.516 E.0697
G1 X157.584 Y113.516 E1.1684
G1 X157.584 Y115.684 E.0697
G1 X155.74 Y115.684 E.0593
G1 X155.74 Y174.884 E1.90366
G1 X154.26 Y174.884 E.04758
G1 X154.26 Y115.684 E1.90366
M73 P40 R9
G1 X141.8 Y115.684 E.40068
; COOLING_NODE: 0
M204 S10000
G1 X142.147 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X142.147 Y175.291 E1.90366
G1 X141.139 Y175.291 E.0324
G1 X141.139 Y185.6 E.33149
G1 X141 Y185.7 E.00552
G1 X140.861 Y185.6 E.00552
G1 X140.861 Y175.291 E.33149
G1 X139.853 Y175.291 E.0324
G1 X139.853 Y116.091 E1.90366
G1 X120.842 Y116.091 E.61134
G1 X120.842 Y113.109 E.09588
G1 X157.991 Y113.109 E1.19458
G1 X157.991 Y116.091 E.09588
G1 X156.147 Y116.091 E.0593
G1 X156.147 Y175.291 E1.90366
G1 X155.139 Y175.291 E.0324
G1 X155.139 Y185.6 E.33149
G1 X155 Y185.7 E.00551
G1 X154.861 Y185.6 E.00551
G1 X154.861 Y175.291 E.33149
G1 X153.853 Y175.291 E.0324
G1 X153.853 Y116.091 E1.90366
G1 X142.207 Y116.091 E.3745
; COOLING_NODE: 0
M204 S10000
G1 X142.554 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X142.554 Y174.902 E1.87806
G1 X143.185 Y174.902 E.02028
G1 X143.185 Y175.698 E.02559
G1 X141.546 Y175.698 E.05268
G1 X141.546 Y185.808 E.32511
G1 X141.153 Y186.091 E.01559
G1 X141.153 Y186.934 E.02709
G3 X140.847 Y186.934 I-.153 J-.555 E.00994
G1 X140.847 Y186.091 E.02709
G1 X140.454 Y185.808 E.01559
G1 X140.454 Y175.698 E.32511
G1 X138.815 Y175.698 E.05268
G1 X138.815 Y174.902 E.02559
G1 X139.446 Y174.902 E.02028
G1 X139.446 Y116.498 E1.87806
G1 X120.435 Y116.498 E.61134
G1 X120.435 Y112.702 E.12206
G1 X158.398 Y112.702 E1.22076
G1 X158.398 Y116.498 E.12206
G1 X156.554 Y116.498 E.0593
G1 X156.554 Y174.902 E1.87806
G1 X157.185 Y174.902 E.02028
G1 X157.185 Y175.698 E.02559
G1 X155.546 Y175.698 E.05268
G1 X155.546 Y185.808 E.32511
G1 X155.153 Y186.091 E.01559
G1 X155.153 Y186.433 E.01101
G3 X154.847 Y186.433 I-.152 J-.545 E.00994
G1 X154.847 Y186.091 E.01099
G1 X154.454 Y185.808 E.01559
G1 X154.454 Y175.698 E.32511
G1 X152.815 Y175.698 E.05268
G1 X152.815 Y174.902 E.02559
G1 X153.446 Y174.902 E.02028
G1 X153.446 Y116.498 E1.87806
G1 X142.614 Y116.498 E.34832
; COOLING_NODE: 0
M204 S250
G1 X142.946 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F3499
M204 S5000
G1 X142.946 Y174.51 E1.7163
G1 X143.577 Y174.51 E.01878
G1 X143.577 Y176.09 E.04706
G1 X141.938 Y176.09 E.0488
G1 X141.938 Y185.998 E.29513
G3 X141.545 Y186.292 I-3.44 J-4.195 E.01464
G1 X141.545 Y187.176 E.02633
G3 X140.455 Y187.176 I-.545 J-.788 E.03452
G1 X140.455 Y186.292 E.02633
G3 X140.062 Y185.998 I3.046 J-4.489 E.01464
G1 X140.062 Y176.09 E.29513
G1 X138.423 Y176.09 E.0488
G1 X138.423 Y174.51 E.04706
G1 X139.054 Y174.51 E.01878
G1 X139.054 Y116.89 E1.7163
G1 X120.077 Y116.89 E.56527
G1 X120.042 Y116.89 E.00102
G1 X120.042 Y112.31 E.13642
G1 X120.077 Y112.31 E.00102
G1 X158.79 Y112.31 E1.15314
G1 X158.79 Y116.89 E.13642
G1 X156.946 Y116.89 E.05493
G1 X156.946 Y174.51 E1.7163
G1 X157.577 Y174.51 E.01878
G1 X157.577 Y176.09 E.04706
M73 P41 R9
G1 X155.938 Y176.09 E.0488
G1 X155.938 Y185.998 E.29513
G3 X155.545 Y186.292 I-3.434 J-4.188 E.01464
G1 X155.545 Y186.676 E.01142
G3 X154.455 Y186.676 I-.545 J-.786 E.03453
G1 X154.455 Y186.292 E.01144
G3 X154.062 Y185.998 I3.04 J-4.481 E.01464
G1 X154.062 Y176.09 E.29513
G1 X152.423 Y176.09 E.0488
G1 X152.423 Y174.51 E.04706
G1 X153.054 Y174.51 E.01878
G1 X153.054 Y116.89 E1.7163
G1 X143.006 Y116.89 E.29929
; WIPE_START
G1 F12000
M204 S8000
G1 X143.005 Y117.89 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.6 I.991 J-.707 P1  F60000
G1 X141 Y115.08 Z1.6
G1 Z1.2
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.62779
G1 F9232.821
M204 S8000
G1 X141.163 Y114.924 E.0104
; LINE_WIDTH: 0.607373
G1 F9566.793
G1 X141.35 Y114.888 E.00848
; LINE_WIDTH: 0.546416
G1 F10725.011
G1 X141.536 Y114.852 E.00756
G1 X154.464 Y114.852 E.51416
; LINE_WIDTH: 0.566538
G1 F10312.872
G1 X154.65 Y114.888 E.00787
; LINE_WIDTH: 0.621728
G1 F9329.517
G1 X154.837 Y114.924 E.00869
G1 X155 Y115.08 E.01029
G1 X155.163 Y114.924 E.01029
; LINE_WIDTH: 0.607373
G1 F9566.793
G1 X155.35 Y114.888 E.00848
; LINE_WIDTH: 0.547363
G1 F10704.882
G1 X155.536 Y114.852 E.00758
G1 X156.752 Y114.852 E.04843
G1 X156.752 Y114.348 E.02005
G1 X155.536 Y114.348 E.04843
; LINE_WIDTH: 0.566538
G1 F10312.872
G1 X155.268 Y114.369 E.01112
; LINE_WIDTH: 0.593761
G1 F9803.197
G1 X155 Y114.389 E.0117
G1 X154.464 Y114.348 E.0234
; LINE_WIDTH: 0.54612
G1 F10731.32
G1 X141.536 Y114.348 E.51385
; LINE_WIDTH: 0.566538
G1 F10312.872
G1 X141.268 Y114.369 E.01112
; LINE_WIDTH: 0.593761
G1 F9803.197
G1 X141 Y114.389 E.0117
G1 X140.464 Y114.348 E.0234
; LINE_WIDTH: 0.54612
G1 F10731.32
G1 X122.081 Y114.348 E.7307
G1 X122.081 Y114.852 E.02
G1 X140.464 Y114.852 E.7307
; LINE_WIDTH: 0.566538
G1 F10312.872
G1 X140.65 Y114.888 E.00787
; LINE_WIDTH: 0.616863
G1 F9408.6
G1 X140.837 Y114.924 E.00862
G1 X140.957 Y115.038 E.00749
; WIPE_START
G1 X140.837 Y114.924 E-.17663
G1 X140.65 Y114.888 E-.20337
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.6 I-1.217 J0 P1  F60000
G1 X140.652 Y174.492 Z1.6
G1 Z1.2
G1 E.4 F1800
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X141.348 Y174.492 E.02072
G1 X141.348 Y115.48 E1.75771
G1 X141.431 Y115.324 E.00528
G1 X141.536 Y115.292 E.00327
G1 X154.464 Y115.292 E.38505
G1 X154.615 Y115.368 E.00504
G1 X154.652 Y115.48 E.00353
G1 X154.652 Y174.492 E1.7577
G1 X155.348 Y174.492 E.02072
G1 X155.348 Y115.48 E1.7577
G1 X155.431 Y115.324 E.00528
G1 X155.536 Y115.292 E.00327
G1 X157.192 Y115.292 E.04931
G1 X157.192 Y113.908 E.04121
G1 X121.641 Y113.908 E1.05892
G1 X121.641 Y115.292 E.04121
G1 X140.464 Y115.292 E.56066
G1 X140.615 Y115.368 E.00504
G1 X140.652 Y115.48 E.00353
G1 X140.652 Y174.432 E1.75592
M204 S10000
G1 X141 Y174.144 F60000
; LINE_WIDTH: 0.36134
G1 F15000
M204 S8000
G1 X141 Y115.54 E1.47405
; WIPE_START
G1 X141 Y116.54 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.6 I-1.183 J.287 P1  F60000
G1 X155 Y174.144 Z1.6
G1 Z1.2
G1 E.4 F1800
G1 F15000
M204 S8000
G1 X155 Y115.54 E1.47405
; COOLING_NODE: 0
; WIPE_START
G1 X155 Y116.54 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.6 I.026 J-1.217 P1  F60000
G1 X114.751 Y115.684 Z1.6
G1 Z1.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X112.416 Y115.684 E.07509
G1 X112.416 Y113.516 E.0697
G1 X114.751 Y113.516 E.07509
G1 X114.751 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X115.158 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X112.009 Y116.091 E.10127
G1 X112.009 Y113.109 E.09588
G1 X115.158 Y113.109 E.10127
G1 X115.158 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X115.565 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X111.602 Y116.498 E.12745
G1 X111.602 Y112.702 E.12206
G1 X115.565 Y112.702 E.12745
G1 X115.565 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X115.923 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F3499
M204 S5000
G1 X111.21 Y116.89 E.1404
G1 X111.21 Y112.31 E.13642
G1 X115.923 Y112.31 E.1404
G1 X115.957 Y112.31 E.00102
G1 X115.957 Y116.864 E.13565
; WIPE_START
G1 F12000
M204 S8000
G1 X114.958 Y116.87 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.6 I1.138 J-.431 P1  F60000
G1 X114.359 Y115.292 Z1.6
G1 Z1.2
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X114.359 Y113.908 E.04121
G1 X112.808 Y113.908 E.0462
G1 X112.808 Y115.292 E.04121
G1 X114.299 Y115.292 E.04441
M204 S10000
G1 X113.919 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X113.919 Y114.348 E.02
G1 X113.248 Y114.348 E.02666
G1 X113.248 Y114.852 E.02
G1 X113.859 Y114.852 E.02427
; CHANGE_LAYER
; Z_HEIGHT: 1.4
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F10731.32
G1 X113.248 Y114.852 E-.23206
G1 X113.248 Y114.462 E-.14794
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 7/27
; update layer progress
M73 L7
M991 S0 P6 ;notify layer change
; OBJECT_ID: 16
; COOLING_NODE: 0
; start printing object, unique label id: 16
M624 BAAAAAAAAAA=
M204 S10000
G17
G3 Z1.6 I-.749 J.959 P1  F60000
G1 X195.07 Y178.408 Z1.6
G1 Z1.4
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X194.745 Y178.398 E.01043
G3 X194.575 Y171.609 I.254 J-3.403 E.3229
G1 X194.915 Y171.583 E.01096
G3 X195.255 Y178.398 I.085 J3.412 E.3393
G1 X195.13 Y178.405 E.00403
; COOLING_NODE: 0
M204 S10000
G1 X195.068 Y178.001 F60000
G1 F13265.217
M204 S8000
G1 X194.776 Y177.993 E.00941
G3 X194.626 Y172.013 I.224 J-2.998 E.28439
G1 X194.925 Y171.991 E.00965
G3 X195.224 Y177.993 I.075 J3.005 E.29885
G1 X195.128 Y177.998 E.0031
; COOLING_NODE: 0
M204 S10000
G1 X195.067 Y177.595 F60000
G1 F13265.217
M204 S8000
G1 X194.806 Y177.588 E.00839
G3 X194.676 Y172.417 I.194 J-2.592 E.2459
G1 X194.935 Y172.398 E.00835
G3 X195.194 Y177.588 I.065 J2.598 E.25839
G1 X195.127 Y177.592 E.00215
; COOLING_NODE: 0
M204 S250
G1 X195.067 Y177.204 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X194.835 Y177.198 E.00689
G3 X194.725 Y172.807 I.164 J-2.201 E.19343
G1 X194.945 Y172.79 E.00657
G3 X195.165 Y177.198 I.055 J2.206 E.20326
G1 X195.126 Y177.2 E.00114
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X194.835 Y177.198 E-.1106
G1 X194.401 Y177.128 E-.16707
G1 X194.151 Y177.029 E-.10233
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I-1.084 J.554 P1  F60000
G1 X201.584 Y191.584 Z1.8
G1 Z1.4
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y191.584 E.42342
G1 X188.416 Y170.416 E.68067
G1 X201.584 Y170.416 E.42342
G1 X201.584 Y191.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y191.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y191.991 E.4496
G1 X188.009 Y170.009 E.70685
G1 X201.991 Y170.009 E.4496
G1 X201.991 Y191.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y192.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y192.398 E.47578
G1 X187.602 Y169.602 E.73303
G1 X202.398 Y169.602 E.47578
G1 X202.398 Y192.338 E.7311
; COOLING_NODE: 1
M204 S250
M73 P42 R9
G1 X202.79 Y192.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y192.79 E.46408
G1 X187.21 Y169.21 E.70237
G1 X202.79 Y169.21 E.46408
G1 X202.79 Y192.73 E.70058
; object ids of layer 7 start: 8,12,16
M624 BwAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer7 end: 8,12,16
M625
; WIPE_START
M204 S8000
G1 X201.79 Y192.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.092 J-.536 P1  F60000
G1 X200.805 Y190.727 Z1.8
G1 Z1.4
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.49672
G1 F11899.515
M204 S8000
G2 X200.801 Y190.825 I-.028 J.048 E.0083
; WIPE_START
G1 X200.748 Y190.825 E-.09081
G1 X200.72 Y190.776 E-.0964
G1 X200.748 Y190.727 E-.0964
G1 X200.805 Y190.727 E-.0964
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I.009 J-1.217 P1  F60000
G1 X189.697 Y190.642 Z1.8
G1 Z1.4
G1 E.4 F1800
; LINE_WIDTH: 0.535452
G1 F10963.765
M204 S8000
G1 X189.36 Y190.346 E.01745
G1 X189.358 Y188.402 E.07564
G1 X188.866 Y188.402 E.01916
G1 X188.866 Y190.303 E.07397
; LINE_WIDTH: 0.516049
G1 F11413.395
G1 X188.847 Y190.599 E.0111
; LINE_WIDTH: 0.477625
G1 F12422.217
G1 X188.827 Y190.895 E.0102
; LINE_WIDTH: 0.427323
G1 F14047.762
G1 X188.808 Y191.192 E.00902
G1 X189.289 Y191.192 E.0146
; LINE_WIDTH: 0.439202
G1 F13626.671
G1 X189.425 Y191.173 E.0043
; LINE_WIDTH: 0.477625
M73 P42 R8
G1 F12422.217
G1 X189.561 Y191.153 E.00472
; LINE_WIDTH: 0.535015
G1 F10973.503
G1 X189.697 Y191.134 E.00534
G1 X200.303 Y191.134 E.41227
; LINE_WIDTH: 0.516049
G1 F11413.395
G1 X200.599 Y191.153 E.0111
; LINE_WIDTH: 0.477625
G1 F12422.217
G1 X200.895 Y191.173 E.0102
; LINE_WIDTH: 0.433565
G1 F13823.318
G1 X201.192 Y191.192 E.00916
G1 X201.182 Y190.711 E.01485
; LINE_WIDTH: 0.46395
G1 F12825.689
G1 X201.158 Y190.507 E.00683
; LINE_WIDTH: 0.534176
G1 F10992.243
G1 X201.134 Y190.303 E.00797
G1 X201.134 Y188.402 E.07378
G1 X200.642 Y188.402 E.01911
G1 X200.642 Y190.303 E.07378
; LINE_WIDTH: 0.51149
G1 F11524.426
G1 X200.589 Y190.373 E.00325
; LINE_WIDTH: 0.482418
G1 F12286.748
G1 X200.536 Y190.443 E.00305
G1 X200.303 Y190.642 E.01063
; LINE_WIDTH: 0.53526
G1 F10968.03
G1 X189.757 Y190.642 E.41014
M204 S10000
G1 X189.252 Y190.727 F60000
; LINE_WIDTH: 0.4967
G1 F11900.039
M204 S8000
G2 X189.249 Y190.825 I-.028 J.048 E.0083
; WIPE_START
G1 X189.195 Y190.825 E-.09082
G1 X189.167 Y190.776 E-.09639
G1 X189.195 Y190.727 E-.09639
G1 X189.252 Y190.727 E-.09639
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.083 J.554 P1  F60000
G1 X195.382 Y178.742 Z1.8
G1 Z1.4
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G3 X194.443 Y178.722 I-.387 J-3.785 E.03029
G1 X191.37 Y190.192 E.38186
G1 X189.808 Y188.585 E.07206
G1 X201.236 Y185.523 E.38043
G1 X201.236 Y186.113 E.01898
G1 X193.632 Y178.509 E.3458
G1 X193.817 Y178.571 E.00628
G1 X188.764 Y179.925 E.16819
; WIPE_START
G1 X189.73 Y179.666 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I-1.135 J-.439 P1  F60000
G1 X188.764 Y182.161 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X188.764 Y181.202 E.03084
G1 X201.236 Y177.86 E.41517
; WIPE_START
G1 X200.27 Y178.119 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.12 J.477 P1  F60000
G1 X201.236 Y175.849 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X201.236 Y176.583 E.0236
G1 X197.804 Y177.503 E.11423
G1 X201.236 Y180.879 E.1548
G1 X201.236 Y180.414 E.01495
G1 X188.764 Y183.756 E.41517
G1 X188.764 Y184.109 E.01135
G1 X194.848 Y190.192 E.27663
G1 X195.201 Y190.192 E.01136
G1 X200.406 Y170.764 E.64676
G1 X199.843 Y170.764 E.0181
G1 X201.236 Y172.157 E.06331
G1 X201.236 Y172.436 E.00899
G1 X196.478 Y190.192 E.59111
G1 X196.592 Y190.192 E.00367
G1 X188.764 Y182.364 E.35597
G1 X188.764 Y182.479 E.00368
G1 X201.236 Y179.137 E.41517
G1 X198.496 Y176.395 E.12466
G2 X198.626 Y176.005 I-1.885 J-.847 E.01323
G1 X201.236 Y175.306 E.08687
G1 X201.236 Y175.646 E.01092
G1 X196.354 Y170.764 E.22198
G1 X196.575 Y170.764 E.0071
G1 X196.385 Y171.498 E.02436
G1 X199.129 Y170.764 E.09135
G1 X198.417 Y173.424 E.08854
G1 X198.452 Y173.498 E.00263
G1 X201.236 Y172.752 E.09266
G1 X201.236 Y172.64 E.00361
; WIPE_START
G1 X201.236 Y172.752 E-.04266
G1 X200.378 Y172.982 E-.33734
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.21 J.127 P1  F60000
G1 X200.61 Y170.764 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X201.236 Y170.764 E.02012
G1 X201.236 Y171.475 E.02284
G1 X197.732 Y172.414 E.11663
M204 S10000
G1 X197.476 Y172.168 F60000
G1 F13265.217
M204 S8000
G1 X197.852 Y170.764 E.04672
G1 X196.779 Y170.764 E.03452
M204 S10000
G1 X196.151 Y170.764 F60000
G1 F13265.217
M204 S8000
G1 X195.298 Y170.764 E.02742
G1 X195.17 Y171.241 E.01587
G1 X195.084 Y171.239 E.00277
G1 X194.61 Y170.764 E.02158
G1 X194.354 Y170.764 E.00821
G1 X188.764 Y172.262 E.1861
G1 X188.764 Y171.897 E.01174
G1 X191.284 Y174.416 E.11456
G3 X191.34 Y174.126 I1.48 J.14 E.00952
G1 X188.764 Y174.816 E.08576
G1 X188.764 Y173.845 E.03123
; WIPE_START
G1 X188.764 Y174.816 E-.36902
G1 X188.792 Y174.809 E-.01098
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I-1.216 J-.059 P1  F60000
G1 X188.764 Y175.386 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X201.236 Y187.857 E.56713
G1 X201.236 Y187.952 E.00304
G1 X200.909 Y187.952 E.01049
G1 X201.236 Y186.735 E.04053
G1 X201.236 Y186.8 E.0021
G1 X189.808 Y189.862 E.38043
G1 X189.808 Y190.192 E.01062
G1 X190.092 Y190.192 E.00915
G1 X193.268 Y178.342 E.39451
G3 X192.51 Y177.82 I1.805 J-3.433 E.02963
; WIPE_START
G1 X193.268 Y178.342 E-.34935
G1 X193.247 Y178.42 E-.03065
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.013 J-.675 P1  F60000
G1 X188.764 Y171.694 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X188.764 Y170.985 E.02278
G1 X189.588 Y170.764 E.02743
G1 X189.376 Y170.764 E.00682
G1 X191.739 Y173.127 E.10744
G3 X192.054 Y172.658 I2.021 J1.019 E.01823
G1 X188.764 Y173.539 E.10952
G1 X188.764 Y173.642 E.00329
G1 X191.497 Y176.374 E.12425
G2 X191.6 Y176.611 I1.236 J-.399 E.00832
G1 X188.764 Y177.371 E.0944
G1 X188.764 Y177.131 E.00771
G1 X200.192 Y188.558 E.51968
G1 X200.192 Y188.357 E.00649
G1 X193.342 Y190.192 E.22805
G1 X193.103 Y190.192 E.00768
G1 X188.764 Y185.854 E.1973
G1 X188.764 Y185.616 E.00765
G1 X191.357 Y175.94 E.32213
G2 X191.427 Y176.183 I1.249 J-.227 E.00816
; WIPE_START
G1 X191.357 Y175.94 E-.09621
G1 X191.164 Y176.661 E-.28379
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.216 J.053 P1  F60000
G1 X191.253 Y174.618 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G2 X191.26 Y175.425 I19.537 J.248 E.02596
G1 X188.764 Y176.094 E.08307
G1 X190.19 Y170.764 E.17739
G1 X190.917 Y170.764 E.02339
; WIPE_START
G1 X190.19 Y170.764 E-.27644
G1 X190.119 Y171.028 E-.10356
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I.079 J1.214 P1  F60000
G1 X194.151 Y170.764 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X194.021 Y170.764 E.00418
G1 X193.846 Y171.417 E.02171
G2 X193.606 Y171.506 I.326 J1.244 E.00824
G1 X192.865 Y170.764 E.0337
G1 X192.744 Y170.764 E.0039
G1 X192.315 Y172.363 E.05323
G3 X192.521 Y172.165 I1.097 J.933 E.0092
G1 X191.121 Y170.764 E.06369
G1 X191.467 Y170.764 E.01113
G1 X188.764 Y180.85 E.33574
G1 X188.764 Y180.62 E.00739
G1 X198.337 Y190.192 E.4353
G1 X198.108 Y190.192 E.00735
G1 X200.192 Y189.634 E.06938
G1 X200.192 Y190.192 E.01796
G1 X200.081 Y190.192 E.00357
G1 X188.764 Y178.875 E.51464
G1 X188.764 Y178.648 E.00732
G1 X192.359 Y177.685 E.11966
G1 X192.21 Y177.524 E.00705
G1 X189.416 Y187.952 E.34716
G1 X189.118 Y187.952 E.00956
G1 X188.764 Y187.598 E.01609
G1 X201.236 Y184.246 E.41526
G1 X201.236 Y184.368 E.00394
G1 X195.584 Y178.717 E.257
G1 X195.728 Y178.692 E.0047
G1 X192.647 Y190.192 E.38286
G1 X191.573 Y190.192 E.03452
; WIPE_START
G1 X192.573 Y190.192 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I0 J1.217 P1  F60000
G1 X193.924 Y190.192 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X197.17 Y178.077 E.40332
G3 X196.877 Y178.265 I-1.088 J-1.37 E.01122
G1 X201.236 Y182.624 E.19821
M204 S10000
G1 X201.236 Y182.969 F60000
G1 F13265.217
M204 S8000
G1 X188.764 Y186.31 E.41517
G1 X188.764 Y187.384 E.03452
; WIPE_START
G1 X188.764 Y186.384 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.217 J0 P1  F60000
G1 X188.764 Y185.033 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X201.236 Y181.692 E.41517
G1 X201.236 Y181.968 E.0089
G1 X199.032 Y190.192 E.27377
; WIPE_START
G1 X199.291 Y189.226 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I-.439 J-1.135 P1  F60000
G1 X196.796 Y190.192 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X197.755 Y190.192 E.03085
G1 X201.236 Y177.202 E.43244
G1 X201.236 Y177.39 E.00604
G1 X198.763 Y174.917 E.11246
G1 X198.751 Y174.695 E.00717
G1 X201.236 Y174.029 E.0827
G1 X201.236 Y173.901 E.00411
G1 X198.099 Y170.764 E.14265
; OBJECT_ID: 12
; COOLING_NODE: 0
; WIPE_START
G1 X198.806 Y171.472 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 16
M625
; start printing object, unique label id: 12
M624 AgAAAAAAAAA=
M204 S10000
G17
G3 Z1.8 I1.217 J-.029 P1  F60000
G1 X197.496 Y117.331 Z1.8
G1 Z1.4
G1 E.4 F1800
; FEATURE: Inner wall
G1 F13265.217
M204 S8000
G1 X197.453 Y117.375 E.00201
G3 X194.575 Y111.609 I-2.453 J-2.377 E.41934
G1 X194.915 Y111.583 E.01097
G3 X197.62 Y117.189 I.085 J3.415 E.25177
G1 X197.536 Y117.285 E.00413
; COOLING_NODE: 0
M204 S10000
G1 X197.218 Y117.024 F60000
G1 F13265.217
M204 S8000
G1 X197.161 Y117.092 E.00285
G3 X194.625 Y112.013 I-2.161 J-2.093 E.36936
G1 X194.925 Y111.991 E.00966
G3 X197.485 Y116.694 I.075 J3.008 E.21231
G1 X197.256 Y116.978 E.01172
; COOLING_NODE: 0
M204 S10000
G1 X196.904 Y116.767 F60000
G1 F13265.217
M204 S8000
G1 X196.869 Y116.808 E.00175
G3 X194.676 Y112.417 I-1.869 J-1.809 E.31938
G1 X194.935 Y112.398 E.00835
G3 X197.148 Y116.465 I.065 J2.6 E.18356
G1 X196.942 Y116.72 E.01057
; COOLING_NODE: 0
M204 S250
G1 X196.602 Y116.519 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X196.587 Y116.535 E.00062
G3 X194.725 Y112.807 I-1.587 J-1.536 E.25125
G1 X194.945 Y112.79 E.00657
G3 X196.824 Y116.244 I.055 J2.208 E.14439
G1 X196.64 Y116.473 E.00877
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X196.587 Y116.535 E-.03074
G1 X196.29 Y116.795 E-.14999
G1 X195.909 Y117.015 E-.16732
G1 X195.829 Y117.041 E-.03196
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I-1.132 J.448 P1  F60000
G1 X201.584 Y131.584 Z1.8
G1 Z1.4
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y131.584 E.42342
G1 X188.416 Y110.416 E.68067
G1 X201.584 Y110.416 E.42342
G1 X201.584 Y131.524 E.67874
; COOLING_NODE: 0
M204 S10000
M73 P43 R8
G1 X201.991 Y131.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y131.991 E.4496
G1 X188.009 Y110.009 E.70685
G1 X201.991 Y110.009 E.4496
G1 X201.991 Y131.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y132.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y132.398 E.47578
G1 X187.602 Y109.602 E.73303
G1 X202.398 Y109.602 E.47578
G1 X202.398 Y132.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y132.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y132.79 E.46408
G1 X187.21 Y109.21 E.70237
G1 X202.79 Y109.21 E.46408
G1 X202.79 Y132.73 E.70058
; WIPE_START
M204 S8000
G1 X201.79 Y132.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.092 J-.536 P1  F60000
G1 X200.805 Y130.727 Z1.8
G1 Z1.4
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.49672
G1 F11899.515
M204 S8000
G2 X200.801 Y130.825 I-.028 J.048 E.0083
; WIPE_START
G1 X200.748 Y130.825 E-.09081
G1 X200.72 Y130.776 E-.0964
G1 X200.748 Y130.727 E-.0964
G1 X200.805 Y130.727 E-.0964
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I.009 J-1.217 P1  F60000
G1 X189.697 Y130.642 Z1.8
G1 Z1.4
G1 E.4 F1800
; LINE_WIDTH: 0.535452
G1 F10963.765
M204 S8000
G1 X189.36 Y130.346 E.01745
G1 X189.358 Y128.402 E.07564
G1 X188.866 Y128.402 E.01916
G1 X188.866 Y130.303 E.07397
; LINE_WIDTH: 0.516049
G1 F11413.395
G1 X188.847 Y130.599 E.0111
; LINE_WIDTH: 0.477625
G1 F12422.217
G1 X188.827 Y130.895 E.0102
; LINE_WIDTH: 0.427323
G1 F14047.762
G1 X188.808 Y131.192 E.00902
G1 X189.289 Y131.192 E.0146
; LINE_WIDTH: 0.439202
G1 F13626.671
G1 X189.425 Y131.173 E.0043
; LINE_WIDTH: 0.477625
G1 F12422.217
G1 X189.561 Y131.153 E.00472
; LINE_WIDTH: 0.535015
G1 F10973.503
G1 X189.697 Y131.134 E.00534
G1 X200.303 Y131.134 E.41227
; LINE_WIDTH: 0.516049
G1 F11413.395
G1 X200.599 Y131.153 E.0111
; LINE_WIDTH: 0.477625
G1 F12422.217
G1 X200.895 Y131.173 E.0102
; LINE_WIDTH: 0.433565
G1 F13823.318
G1 X201.192 Y131.192 E.00916
G1 X201.182 Y130.711 E.01485
; LINE_WIDTH: 0.46395
G1 F12825.689
G1 X201.158 Y130.507 E.00683
; LINE_WIDTH: 0.534176
G1 F10992.243
G1 X201.134 Y130.303 E.00797
G1 X201.134 Y128.402 E.07378
G1 X200.642 Y128.402 E.01911
G1 X200.642 Y130.303 E.07378
; LINE_WIDTH: 0.51149
G1 F11524.426
G1 X200.589 Y130.373 E.00325
; LINE_WIDTH: 0.482418
G1 F12286.748
G1 X200.536 Y130.443 E.00305
G1 X200.303 Y130.642 E.01063
; LINE_WIDTH: 0.53526
G1 F10968.03
G1 X189.757 Y130.642 E.41014
M204 S10000
G1 X189.252 Y130.727 F60000
; LINE_WIDTH: 0.4967
G1 F11900.039
M204 S8000
G2 X189.249 Y130.825 I-.028 J.048 E.0083
; WIPE_START
G1 X189.195 Y130.825 E-.09082
G1 X189.167 Y130.776 E-.09639
G1 X189.195 Y130.727 E-.09639
G1 X189.252 Y130.727 E-.09639
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.083 J.554 P1  F60000
G1 X195.383 Y118.744 Z1.8
G1 Z1.4
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G3 X194.443 Y118.722 I-.378 J-3.904 E.0303
G1 X191.37 Y130.192 E.38186
G1 X189.808 Y128.585 E.07206
G1 X201.236 Y125.523 E.38043
G1 X201.236 Y126.113 E.01898
G1 X193.632 Y118.509 E.3458
G1 X193.817 Y118.571 E.00628
G1 X188.764 Y119.925 E.16819
; WIPE_START
G1 X189.73 Y119.666 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I-1.135 J-.439 P1  F60000
G1 X188.764 Y122.161 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X188.764 Y121.202 E.03084
G1 X201.236 Y117.86 E.41517
; WIPE_START
G1 X200.27 Y118.119 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.12 J.477 P1  F60000
G1 X201.236 Y115.849 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X201.236 Y116.583 E.0236
G1 X197.806 Y117.502 E.11417
G1 X201.236 Y120.879 E.15478
G1 X201.236 Y120.414 E.01495
G1 X188.764 Y123.756 E.41517
G1 X188.764 Y124.109 E.01135
G1 X194.848 Y130.192 E.27663
G1 X195.201 Y130.192 E.01136
G1 X200.406 Y110.764 E.64676
G1 X199.843 Y110.764 E.0181
G1 X201.236 Y112.157 E.06331
G1 X201.236 Y112.436 E.00899
G1 X196.478 Y130.192 E.59111
G1 X196.592 Y130.192 E.00367
G1 X188.764 Y122.364 E.35597
G1 X188.764 Y122.479 E.00368
G1 X201.236 Y119.137 E.41517
G1 X198.496 Y116.395 E.12466
G2 X198.626 Y116.005 I-1.886 J-.847 E.01323
G1 X201.236 Y115.306 E.08687
G1 X201.236 Y115.646 E.01092
G1 X196.354 Y110.764 E.22198
G1 X196.575 Y110.764 E.0071
G1 X196.385 Y111.498 E.02436
G1 X199.129 Y110.764 E.09135
G1 X198.417 Y113.424 E.08854
G1 X198.452 Y113.498 E.00263
G1 X201.236 Y112.752 E.09266
G1 X201.236 Y112.64 E.00361
; WIPE_START
G1 X201.236 Y112.752 E-.04266
G1 X200.378 Y112.982 E-.33734
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.21 J.127 P1  F60000
G1 X200.61 Y110.764 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X201.236 Y110.764 E.02012
G1 X201.236 Y111.475 E.02284
G1 X197.732 Y112.414 E.11663
M204 S10000
G1 X197.476 Y112.168 F60000
G1 F13265.217
M204 S8000
G1 X197.852 Y110.764 E.04672
G1 X196.779 Y110.764 E.03452
M204 S10000
G1 X196.151 Y110.764 F60000
G1 F13265.217
M204 S8000
G1 X195.298 Y110.764 E.02742
G1 X195.17 Y111.241 E.01587
G1 X195.084 Y111.239 E.00277
G1 X194.61 Y110.764 E.02158
G1 X194.354 Y110.764 E.00821
G1 X188.764 Y112.262 E.1861
G1 X188.764 Y111.897 E.01174
G1 X191.284 Y114.416 E.11456
G3 X191.34 Y114.126 I1.481 J.14 E.00952
G1 X188.764 Y114.816 E.08576
G1 X188.764 Y113.845 E.03123
; WIPE_START
G1 X188.764 Y114.816 E-.36902
G1 X188.792 Y114.809 E-.01098
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I-1.216 J-.059 P1  F60000
G1 X188.764 Y115.386 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X201.236 Y127.857 E.56713
G1 X201.236 Y127.952 E.00304
G1 X200.909 Y127.952 E.01049
G1 X201.236 Y126.735 E.04053
G1 X201.236 Y126.8 E.0021
G1 X189.808 Y129.862 E.38043
G1 X189.808 Y130.192 E.01062
G1 X190.092 Y130.192 E.00915
G1 X193.267 Y118.344 E.39445
G3 X192.51 Y117.82 I1.877 J-3.524 E.02965
; WIPE_START
G1 X193.267 Y118.344 E-.34958
G1 X193.247 Y118.421 E-.03042
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.013 J-.675 P1  F60000
G1 X188.764 Y111.694 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X188.764 Y110.985 E.02278
G1 X189.588 Y110.764 E.02743
G1 X189.376 Y110.764 E.00682
G1 X191.737 Y113.125 E.10736
G3 X192.055 Y112.658 I2.497 J1.356 E.01821
G1 X188.764 Y113.539 E.10954
G1 X188.764 Y113.642 E.00329
G1 X191.497 Y116.374 E.12425
G2 X191.6 Y116.611 I1.236 J-.399 E.00832
G1 X188.764 Y117.371 E.0944
G1 X188.764 Y117.131 E.00771
G1 X200.192 Y128.558 E.51968
G1 X200.192 Y128.357 E.00649
G1 X193.342 Y130.192 E.22805
G1 X193.103 Y130.192 E.00768
G1 X188.764 Y125.854 E.1973
G1 X188.764 Y125.616 E.00765
G1 X191.357 Y115.939 E.32213
G2 X191.427 Y116.183 I1.249 J-.227 E.00816
; WIPE_START
G1 X191.357 Y115.939 E-.09621
G1 X191.164 Y116.661 E-.28379
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.216 J.053 P1  F60000
G1 X191.253 Y114.618 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G2 X191.26 Y115.425 I19.536 J.248 E.02596
G1 X188.764 Y116.094 E.08307
G1 X190.19 Y110.764 E.17739
G1 X190.917 Y110.764 E.02339
; WIPE_START
G1 X190.19 Y110.764 E-.27644
G1 X190.119 Y111.028 E-.10356
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I.079 J1.214 P1  F60000
G1 X194.151 Y110.764 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X194.021 Y110.764 E.00418
G1 X193.846 Y111.417 E.02171
G2 X193.606 Y111.506 I.326 J1.246 E.00824
G1 X192.865 Y110.764 E.0337
G1 X192.744 Y110.764 E.0039
G1 X192.312 Y112.377 E.05368
G3 X192.521 Y112.165 I.955 J.735 E.0096
G1 X191.121 Y110.764 E.06369
G1 X191.467 Y110.764 E.01113
G1 X188.764 Y120.85 E.33574
G1 X188.764 Y120.62 E.00739
G1 X198.337 Y130.192 E.4353
G1 X198.108 Y130.192 E.00735
G1 X200.192 Y129.634 E.06938
G1 X200.192 Y130.192 E.01796
G1 X200.081 Y130.192 E.00357
G1 X188.764 Y118.875 E.51464
G1 X188.764 Y118.648 E.00732
G1 X192.359 Y117.685 E.11966
G1 X192.21 Y117.524 E.00705
G1 X189.416 Y127.952 E.34716
G1 X189.118 Y127.952 E.00956
G1 X188.764 Y127.598 E.01609
G1 X201.236 Y124.246 E.41526
G1 X201.236 Y124.368 E.00394
G1 X195.584 Y118.717 E.257
G1 X195.728 Y118.692 E.0047
G1 X192.647 Y130.192 E.38286
G1 X191.573 Y130.192 E.03452
; WIPE_START
G1 X192.573 Y130.192 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I0 J1.217 P1  F60000
G1 X193.924 Y130.192 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X197.17 Y118.077 E.40332
G3 X196.877 Y118.265 I-1.093 J-1.377 E.01122
G1 X201.236 Y122.624 E.19821
M204 S10000
G1 X201.236 Y122.969 F60000
G1 F13265.217
M204 S8000
G1 X188.764 Y126.31 E.41517
G1 X188.764 Y127.384 E.03452
; WIPE_START
G1 X188.764 Y126.384 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.217 J0 P1  F60000
G1 X188.764 Y125.033 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X201.236 Y121.692 E.41517
G1 X201.236 Y121.968 E.0089
G1 X199.032 Y130.192 E.27377
; WIPE_START
G1 X199.291 Y129.226 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I-.439 J-1.135 P1  F60000
G1 X196.796 Y130.192 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X197.755 Y130.192 E.03085
G1 X201.236 Y117.202 E.43244
G1 X201.236 Y117.39 E.00604
G1 X198.763 Y114.917 E.11246
G1 X198.751 Y114.695 E.00717
G1 X201.236 Y114.029 E.0827
G1 X201.236 Y113.901 E.00411
G1 X198.099 Y110.764 E.14265
; OBJECT_ID: 8
; COOLING_NODE: 0
; WIPE_START
G1 X198.806 Y111.472 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 12
M625
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z1.8 I-.089 J-1.214 P1  F60000
G1 X141.654 Y115.684 Z1.8
G1 Z1.4
G1 E.4 F1800
; FEATURE: Inner wall
G1 F13265.217
M204 S8000
G1 X141.654 Y174.884 E1.90366
G1 X140.346 Y174.884 E.04209
G1 X140.346 Y115.684 E1.90366
M73 P44 R8
G1 X121.148 Y115.684 E.61734
G1 X121.148 Y113.516 E.0697
G1 X157.584 Y113.516 E1.17166
G1 X157.584 Y115.684 E.0697
G1 X155.654 Y115.684 E.06204
G1 X155.654 Y174.884 E1.90366
G1 X154.346 Y174.884 E.04209
G1 X154.346 Y115.684 E1.90366
G1 X141.714 Y115.684 E.40617
; COOLING_NODE: 0
M204 S10000
G1 X142.062 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X142.062 Y175.291 E1.90366
G1 X139.938 Y175.291 E.06827
G1 X139.938 Y116.091 E1.90366
G1 X120.74 Y116.091 E.61734
G1 X120.74 Y113.109 E.09588
G1 X157.991 Y113.109 E1.19784
G1 X157.991 Y116.091 E.09588
G1 X156.062 Y116.091 E.06204
G1 X156.062 Y175.291 E1.90366
G1 X153.938 Y175.291 E.06827
G1 X153.938 Y116.091 E1.90366
G1 X142.122 Y116.091 E.37999
; COOLING_NODE: 0
M204 S10000
G1 X142.469 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X142.469 Y174.902 E1.87806
G1 X143.12 Y174.902 E.02093
G1 X143.12 Y175.698 E.02559
G1 X141.377 Y175.698 E.05603
G1 X141.377 Y184.693 E.28924
G3 X140.623 Y184.693 I-.377 J-1.87 E.02442
G1 X140.623 Y175.698 E.28924
G1 X138.88 Y175.698 E.05603
G1 X138.88 Y174.902 E.02559
G1 X139.531 Y174.902 E.02093
G1 X139.531 Y116.498 E1.87806
G1 X120.333 Y116.498 E.61734
G1 X120.333 Y112.702 E.12206
G1 X158.398 Y112.702 E1.22402
G1 X158.398 Y116.498 E.12206
G1 X156.469 Y116.498 E.06204
G1 X156.469 Y174.902 E1.87806
G1 X157.12 Y174.902 E.02093
G1 X157.12 Y175.698 E.02559
G1 X155.377 Y175.698 E.05603
G1 X155.377 Y185.773 E.32396
G1 X155 Y185.952 E.01343
G1 X154.623 Y185.773 E.01343
G1 X154.623 Y175.698 E.32396
G1 X152.88 Y175.698 E.05603
G1 X152.88 Y174.902 E.02559
G1 X153.531 Y174.902 E.02093
G1 X153.531 Y116.498 E1.87806
G1 X142.529 Y116.498 E.35381
; COOLING_NODE: 0
M204 S250
G1 X142.861 Y116.89 F60000
M106 S127.5
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F3411
M204 S5000
G1 X142.861 Y174.51 E1.7163
G1 X143.512 Y174.51 E.01939
G1 X143.512 Y176.09 E.04706
G1 X141.769 Y176.09 E.0519
G1 X141.769 Y185.987 E.29479
G3 X141.247 Y186.268 I-1.68 J-2.486 E.01769
G1 X141.247 Y187.144 E.02607
G3 X140.753 Y187.144 I-.248 J-.976 E.01489
G1 X140.753 Y186.268 E.02608
G3 X140.231 Y185.987 I1.157 J-2.767 E.01769
G1 X140.231 Y176.09 E.29479
G1 X138.488 Y176.09 E.0519
G1 X138.488 Y174.51 E.04706
G1 X139.139 Y174.51 E.01939
G1 X139.139 Y116.89 E1.7163
G1 X121.201 Y116.89 E.53431
G1 X120.801 Y116.89 E.01191
G1 X120.401 Y116.89 E.01191
G1 X120.001 Y116.89 E.01191
G1 X119.941 Y116.89 E.00179
G1 X119.941 Y112.31 E.13642
M106 S58.65
G1 X120.001 Y112.31 E.00179
G1 X120.401 Y112.31 E.01191
G1 X120.801 Y112.31 E.01191
G1 X121.201 Y112.31 E.01191
G1 X158.79 Y112.31 E1.11963
G1 X158.79 Y116.89 E.13642
G1 X156.861 Y116.89 E.05747
M73 P45 R8
G1 X156.861 Y174.51 E1.7163
G1 X157.512 Y174.51 E.01939
G1 X157.512 Y176.09 E.04706
G1 X155.769 Y176.09 E.0519
G1 X155.769 Y185.987 E.29479
G3 X155.247 Y186.268 I-1.68 J-2.486 E.01769
G1 X155.247 Y186.644 E.01117
G3 X154.753 Y186.643 I-.246 J-.964 E.0149
G1 X154.753 Y186.268 E.01115
G3 X154.231 Y185.987 I1.157 J-2.767 E.01769
G1 X154.231 Y176.09 E.29479
G1 X152.488 Y176.09 E.0519
G1 X152.488 Y174.51 E.04706
G1 X153.139 Y174.51 E.01939
G1 X153.139 Y116.89 E1.7163
G1 X142.921 Y116.89 E.30438
; WIPE_START
G1 F12000
M204 S8000
G1 X142.92 Y117.89 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I.972 J-.732 P1  F60000
G1 X140.785 Y115.053 Z1.8
G1 Z1.4
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X141.103 Y113.864 E.03956
G1 X141.93 Y113.864 E.02657
M204 S10000
G1 X142.584 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X143.658 Y113.864 E.03452
G1 X143.263 Y115.336 E.04897
G1 X143.604 Y115.336 E.01096
G1 X142.133 Y113.864 E.0669
G1 X142.381 Y113.864 E.00795
G1 X141.986 Y115.336 E.04897
G1 X141.86 Y115.336 E.00407
G1 X140.389 Y113.864 E.0669
G1 X140.232 Y113.864 E.00503
G1 X134.742 Y115.336 E.18277
G1 X134.882 Y115.336 E.00448
G1 X133.411 Y113.864 E.0669
G1 X133.047 Y115.336 E.04873
G1 X133.137 Y115.336 E.0029
G1 X131.666 Y113.864 E.0669
G1 X132.164 Y113.864 E.01601
G1 X131.77 Y115.336 E.04897
G1 X131.393 Y115.336 E.01213
G1 X129.921 Y113.864 E.0669
M204 S10000
G1 X129.61 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X129.216 Y115.336 E.04897
G1 X128.142 Y115.336 E.03452
M204 S10000
G1 X127.7 Y115.336 F60000
G1 F13265.217
M204 S8000
G1 X126.661 Y115.336 E.0334
G1 X127.056 Y113.864 E.04897
G1 X126.432 Y113.864 E.02004
G1 X127.903 Y115.336 E.0669
G1 X128.333 Y113.864 E.04928
G1 X128.177 Y113.864 E.00501
G1 X129.648 Y115.336 E.0669
G1 X129.976 Y115.336 E.01055
G1 X135.466 Y113.864 E.18277
G1 X135.155 Y113.864 E.01
G1 X136.626 Y115.336 E.0669
G1 X136.878 Y115.336 E.0081
G1 X137.272 Y113.864 E.04897
G1 X136.9 Y113.864 E.01198
G1 X138.371 Y115.336 E.0669
G1 X138.155 Y115.336 E.00693
G1 X138.549 Y113.864 E.04897
G1 X138.644 Y113.864 E.00305
G1 X140.115 Y115.336 E.0669
; WIPE_START
G1 X139.408 Y114.628 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.067 J.584 P1  F60000
G1 X139.826 Y113.864 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X139.432 Y115.336 E.04897
G1 X144.999 Y113.864 E.18514
G1 X144.935 Y113.864 E.00205
G1 X144.541 Y115.336 E.04897
G1 X144.275 Y115.336 E.00855
G1 X149.765 Y113.864 E.18277
G1 X150.043 Y113.864 E.00895
G1 X149.649 Y115.336 E.04897
; WIPE_START
G1 X149.908 Y114.37 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I.652 J-1.028 P1  F60000
G1 X149.111 Y113.864 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X150.582 Y115.336 E.0669
G1 X150.926 Y115.336 E.01105
G1 X151.32 Y113.864 E.04897
G1 X150.856 Y113.864 E.01493
G1 X152.327 Y115.336 E.0669
G1 X152.203 Y115.336 E.00398
G1 X152.6 Y113.864 E.049
G1 X154.071 Y115.336 E.0669
G1 X153.807 Y115.336 E.00851
G1 X154.487 Y115.153 E.02263
G1 X154.346 Y115.336 E.0074
G1 X154.275 Y115.336 E.00229
; WIPE_START
G1 X154.346 Y115.336 E-.02701
G1 X154.487 Y115.153 E-.0874
G1 X153.811 Y115.334 E-.2656
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.216 J.052 P1  F60000
G1 X153.874 Y113.864 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X153.48 Y115.336 E.04897
G1 X152.53 Y115.336 E.03054
; WIPE_START
G1 X153.48 Y115.336 E-.36088
G1 X153.493 Y115.287 E-.01912
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I.622 J1.046 P1  F60000
G1 X155.886 Y113.864 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X155.151 Y113.864 E.02362
G1 X154.833 Y115.053 E.03956
G1 X157.236 Y114.417 E.07992
G1 X157.236 Y115.011 E.01909
G1 X156.089 Y113.864 E.05212
G1 X156.428 Y113.864 E.0109
G1 X156.034 Y115.336 E.04897
G1 X155.816 Y115.336 E.00702
G1 X154.345 Y113.864 E.0669
G1 X154.531 Y113.864 E.00598
G1 X149.041 Y115.336 E.18277
G1 X148.838 Y115.336 E.00652
G1 X147.367 Y113.864 E.0669
G1 X147.489 Y113.864 E.00393
G1 X147.093 Y115.336 E.04898
G1 X145.622 Y113.864 E.0669
G1 X146.212 Y113.864 E.01896
G1 X145.818 Y115.336 E.04897
G1 X146.89 Y115.336 E.03448
M204 S10000
G1 X147.298 Y115.336 F60000
G1 F13265.217
M204 S8000
G1 X148.372 Y115.336 E.03452
G1 X148.766 Y113.864 E.04897
; WIPE_START
G1 X148.507 Y114.83 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I-.192 J-1.202 P1  F60000
G1 X145.349 Y115.336 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X143.878 Y113.864 E.0669
; WIPE_START
G1 X144.585 Y114.572 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I.109 J-1.212 P1  F60000
G1 X136.696 Y113.864 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X135.995 Y113.864 E.02254
G1 X135.601 Y115.336 E.04897
; WIPE_START
G1 X135.86 Y114.37 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I.492 J-1.113 P1  F60000
G1 X134.718 Y113.864 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X134.324 Y115.336 E.04897
G1 X133.341 Y115.336 E.03162
; WIPE_START
G1 X134.324 Y115.336 E-.37363
G1 X134.328 Y115.319 E-.00637
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I-.005 J-1.217 P1  F60000
G1 X130.493 Y115.336 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X130.887 Y113.864 E.04897
G1 X130.7 Y113.864 E.006
G1 X125.21 Y115.336 E.18277
G1 X125.384 Y115.336 E.00561
G1 X125.778 Y113.864 E.04897
G1 X125.934 Y113.864 E.005
G1 X121.496 Y115.054 E.14775
G1 X121.496 Y115.336 E.00906
G1 X121.553 Y115.336 E.00184
G1 X121.947 Y113.864 E.04897
G1 X121.496 Y113.864 E.01451
G1 X121.496 Y114.161 E.00955
G1 X122.67 Y115.336 E.05339
G1 X122.83 Y115.336 E.00515
G1 X123.224 Y113.864 E.04897
G1 X122.943 Y113.864 E.00903
G1 X124.414 Y115.336 E.0669
G1 X124.107 Y115.336 E.00988
G1 X124.501 Y113.864 E.04897
G1 X123.428 Y113.864 E.03452
; WIPE_START
G1 X124.428 Y113.864 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I0 J1.217 P1  F60000
G1 X124.688 Y113.864 Z1.8
G1 Z1.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X126.159 Y115.336 E.0669
; WIPE_START
G1 X125.452 Y114.628 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I-1.179 J.302 P1  F60000
M106 S127.5
G1 X140.775 Y174.455 Z1.8
G1 Z1.4
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.49387
G1 F11974.72
M204 S8000
G1 X141.225 Y174.455 E.01606
G1 X141.225 Y115.488 E2.10049
G1 X140.775 Y115.482 E.01607
G1 X140.775 Y174.395 E2.09859
; WIPE_START
G1 X140.775 Y173.395 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I-1.21 J.13 P1  F60000
G1 X141 Y175.495 Z1.8
G1 Z1.4
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.390139
G1 F15000
M204 S8000
G1 X141 Y184.351 E.24293
G1 X141.129 Y184.513 E.00568
M204 S10000
G1 X140.608 Y185.085 F60000
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X140.608 Y185.771 E.02042
G1 X141 Y185.967 E.01305
G1 X141.392 Y185.771 E.01305
G1 X141.392 Y185.085 E.02042
G3 X140.668 Y185.091 I-.378 J-1.881 E.02171
; WIPE_START
G1 X140.981 Y185.123 E-.11982
G1 X141.392 Y185.085 E-.15676
G1 X141.392 Y185.358 E-.10342
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I-.028 J1.217 P1  F60000
G1 X154.87 Y185.665 Z1.8
G1 Z1.4
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.39014
G1 F15000
M204 S8000
G1 X155 Y185.534 E.00505
G1 X155 Y175.495 E.27537
; WIPE_START
G1 X155 Y176.495 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.21 J-.134 P1  F60000
G1 X154.775 Y174.455 Z1.8
G1 Z1.4
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.493875
G1 F11974.586
M204 S8000
G1 X155.225 Y174.455 E.01606
G1 X155.225 Y115.488 E2.10051
G1 X154.775 Y115.482 E.01607
G1 X154.775 Y174.395 E2.09861
; WIPE_START
M73 P46 R8
G1 X154.775 Y173.395 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I-1.217 J.026 P1  F60000
G1 X155.051 Y186.158 Z1.8
G1 Z1.4
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.142059
G1 F15000
M204 S8000
G1 X155 Y186.221 E.00064
G1 X155 Y186.477 E.00201
; COOLING_NODE: 0
; WIPE_START
G1 X155 Y186.221 E-.28848
G1 X155.051 Y186.158 E-.09152
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.057 J-.603 P1  F60000
G1 X114.852 Y115.684 Z1.8
G1 Z1.4
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X112.416 Y115.684 E.07834
G1 X112.416 Y113.516 E.0697
G1 X114.852 Y113.516 E.07834
G1 X114.852 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X115.26 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X112.009 Y116.091 E.10452
G1 X112.009 Y113.109 E.09588
G1 X115.26 Y113.109 E.10452
G1 X115.26 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X115.667 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X111.602 Y116.498 E.1307
G1 X111.602 Y112.702 E.12206
G1 X115.667 Y112.702 E.1307
G1 X115.667 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X115.998 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F3411
M204 S5000
G1 X111.21 Y116.89 E.14263
G1 X111.21 Y112.31 E.13642
G1 X114.798 Y112.31 E.10689
G1 X115.198 Y112.31 E.01191
G1 X115.598 Y112.31 E.01191
G1 X115.998 Y112.31 E.01191
G1 X116.059 Y112.31 E.00179
G1 X116.059 Y116.89 E.13642
M106 S58.65
G1 X116.058 Y116.89 E.00001
; WIPE_START
G1 F8400.483
M204 S8000
G1 X115.058 Y116.89 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z1.8 I1.14 J-.427 P1  F60000
G1 X114.46 Y115.292 Z1.8
G1 Z1.4
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X114.46 Y113.908 E.04121
G1 X112.808 Y113.908 E.04921
G1 X112.808 Y115.292 E.04121
G1 X114.4 Y115.292 E.04742
M204 S10000
G1 X114.02 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X114.02 Y114.348 E.02
G1 X113.248 Y114.348 E.03068
G1 X113.248 Y114.852 E.02
G1 X113.96 Y114.852 E.0283
; CHANGE_LAYER
; Z_HEIGHT: 1.6
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F10731.32
G1 X113.248 Y114.852 E-.27051
G1 X113.248 Y114.563 E-.10949
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 8/27
; update layer progress
M73 L8
M991 S0 P7 ;notify layer change
; OBJECT_ID: 16
; COOLING_NODE: 0
; start printing object, unique label id: 16
M624 BAAAAAAAAAA=
M204 S10000
G17
G3 Z1.8 I-.748 J.96 P1  F60000
G1 X195.166 Y178.411 Z1.8
G1 Z1.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X195.085 Y178.413 E.00262
G3 X194.575 Y171.609 I-.085 J-3.415 E.33412
G1 X194.915 Y171.583 E.01096
G3 X195.425 Y178.387 I.085 J3.415 E.33412
G1 X195.226 Y178.405 E.0064
; COOLING_NODE: 0
M204 S10000
G1 X195.136 Y178.005 F60000
G1 F13265.217
M204 S8000
G1 X195.075 Y178.006 E.00196
G3 X194.626 Y172.013 I-.075 J-3.008 E.29427
G1 X194.925 Y171.991 E.00965
G3 X195.374 Y177.983 I.075 J3.008 E.29428
G1 X195.196 Y177.999 E.00575
; COOLING_NODE: 0
M204 S10000
G1 X195.106 Y177.599 F60000
G1 F13265.217
M204 S8000
G1 X195.065 Y177.599 E.00131
G3 X194.676 Y172.417 I-.065 J-2.6 E.25443
G1 X194.935 Y172.398 E.00835
G3 X195.323 Y177.579 I.065 J2.6 E.25444
G1 X195.165 Y177.594 E.0051
; COOLING_NODE: 0
M204 S250
G1 X195.076 Y177.207 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X195.055 Y177.207 E.00061
G3 X194.725 Y172.807 I-.055 J-2.208 E.20014
G1 X194.945 Y172.79 E.00657
G3 X195.491 Y177.152 I.055 J2.208 E.19358
G1 X195.135 Y177.199 E.0107
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X195.055 Y177.207 E-.03052
G1 X194.619 Y177.177 E-.16612
G1 X194.193 Y177.058 E-.16824
G1 X194.157 Y177.039 E-.01512
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I-1.084 J.553 P1  F60000
G1 X201.584 Y191.584 Z2
G1 Z1.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y191.584 E.42342
G1 X188.416 Y170.416 E.68067
G1 X201.584 Y170.416 E.42342
G1 X201.584 Y191.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y191.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y191.991 E.4496
G1 X188.009 Y170.009 E.70685
G1 X201.991 Y170.009 E.4496
G1 X201.991 Y191.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y192.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y192.398 E.47578
G1 X187.602 Y169.602 E.73303
G1 X202.398 Y169.602 E.47578
G1 X202.398 Y192.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y192.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y192.79 E.46408
G1 X187.21 Y169.21 E.70237
G1 X202.79 Y169.21 E.46408
G1 X202.79 Y192.73 E.70058
; object ids of layer 8 start: 8,12,16
M624 BwAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer8 end: 8,12,16
M625
; WIPE_START
M204 S8000
G1 X201.79 Y192.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I.949 J-.761 P1  F60000
G1 X199.751 Y190.192 Z2
G1 Z1.6
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X200.163 Y190.192 E.01323
G1 X200.192 Y190.082 E.00365
G1 X188.764 Y178.675 E.51921
G1 X188.764 Y178.794 E.00382
G1 X192.484 Y177.797 E.12384
G3 X192.097 Y177.398 I3.25 J-3.54 E.0179
G1 X189.269 Y187.952 E.35135
G1 X189.318 Y187.952 E.00158
G1 X188.764 Y187.398 E.02519
G1 X188.764 Y187.734 E.01079
G1 X201.236 Y184.392 E.41517
G1 X201.236 Y184.168 E.0072
G1 X195.754 Y178.687 E.24927
G1 X195.574 Y178.719 E.00587
G1 X192.5 Y190.192 E.38196
G1 X193.303 Y190.192 E.02582
G1 X188.764 Y185.654 E.20639
G1 X188.764 Y186.457 E.02583
G1 X201.236 Y183.115 E.41517
G1 X201.236 Y183.965 E.02733
; WIPE_START
G1 X201.236 Y183.115 E-.32292
G1 X201.09 Y183.154 E-.05708
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I1.214 J.078 P1  F60000
G1 X201.236 Y180.883 Z2
G1 Z1.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X201.236 Y181.422 E.01734
G1 X198.858 Y190.192 E.29219
M204 S10000
G1 X198.333 Y190.192 F60000
G1 F13265.217
M204 S8000
G1 X197.609 Y190.192 E.0233
G1 X201.236 Y176.656 E.45063
G1 X201.236 Y176.73 E.00237
G1 X197.622 Y177.698 E.1203
G2 X197.924 Y177.368 I-1.498 J-1.675 E.01442
G1 X201.236 Y180.679 E.15059
G1 X201.236 Y180.561 E.00381
G1 X188.764 Y183.902 E.41517
M204 S10000
G1 X188.764 Y183.909 F60000
G1 F13265.217
M204 S8000
G1 X195.048 Y190.192 E.28573
M204 S10000
G1 X195.054 Y190.192 F60000
G1 F13265.217
M204 S8000
G1 X200.26 Y170.764 E.64676
G1 X200.043 Y170.764 E.00696
G1 X201.236 Y171.957 E.05422
G1 X201.236 Y171.89 E.00215
G1 X196.331 Y190.192 E.6093
G1 X196.792 Y190.192 E.01481
G1 X188.764 Y182.164 E.36506
G1 X188.764 Y182.625 E.01482
G1 X201.236 Y179.284 E.41517
G1 X201.236 Y178.935 E.01122
G1 X198.546 Y176.246 E.1223
M204 S10000
G1 X198.578 Y176.164 F60000
G1 F13265.217
M204 S8000
G1 X201.236 Y175.446 E.08851
G1 X196.554 Y170.764 E.21288
G1 X196.429 Y170.764 E.00404
G1 X196.245 Y171.45 E.02281
G3 X196.588 Y171.589 I-.527 J1.785 E.01193
G1 X199.667 Y170.764 E.1025
G1 X199.271 Y170.764 E.01275
M204 S10000
G1 X198.983 Y170.764 F60000
G1 F13265.217
M204 S8000
G1 X198.323 Y173.229 E.08204
G3 X198.505 Y173.63 I-1.91 J1.11 E.01419
G1 X201.236 Y172.898 E.09091
; WIPE_START
G1 X200.27 Y173.157 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I1.213 J.099 P1  F60000
G1 X200.464 Y170.764 Z2
G1 Z1.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X201.236 Y170.764 E.02481
G1 X201.236 Y171.621 E.02755
G1 X197.841 Y172.531 E.11301
G2 X197.358 Y172.063 I-2.579 J2.182 E.02166
G1 X197.706 Y170.764 E.04324
G1 X198.299 Y170.764 E.01907
G1 X201.236 Y173.701 E.13355
G1 X201.236 Y174.175 E.01525
G1 X198.759 Y174.839 E.08246
G1 X198.752 Y174.707 E.00426
G1 X201.236 Y177.19 E.11294
; WIPE_START
G1 X200.528 Y176.483 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I-1.161 J.365 P1  F60000
G1 X201.236 Y178.731 Z2
G1 Z1.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X201.236 Y178.007 E.0233
G1 X188.764 Y181.348 E.41517
G1 X188.764 Y180.623 E.02331
M204 S10000
G1 X188.764 Y180.1 F60000
G1 F13265.217
M204 S8000
G1 X194.08 Y178.647 E.1772
G3 X193.933 Y178.61 I.111 J-.757 E.00489
G1 X201.236 Y185.913 E.3321
G1 X201.236 Y185.669 E.00784
G1 X189.808 Y188.731 E.38043
G1 X189.808 Y188.442 E.00932
G1 X191.558 Y190.192 E.07961
G1 X191.223 Y190.192 E.01078
G1 X194.303 Y178.698 E.38265
G2 X195.373 Y178.745 I.806 J-6.171 E.03448
; WIPE_START
G1 X194.719 Y178.756 E-.24864
G1 X194.376 Y178.708 E-.13136
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I.302 J-1.179 P1  F60000
G1 X193.74 Y178.545 Z2
G1 Z1.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G3 X193.14 Y178.27 I1.301 J-3.628 E.02123
G1 X189.946 Y190.192 E.39688
G1 X189.808 Y190.192 E.00444
G1 X189.808 Y190.008 E.00591
G1 X201.236 Y186.946 E.38043
M204 S10000
G1 X201.236 Y186.585 F60000
G1 F13265.217
M204 S8000
G1 X201.236 Y186.188 E.01275
G1 X200.763 Y187.952 E.05872
G1 X201.236 Y187.952 E.0152
G1 X201.236 Y187.657 E.00947
G1 X188.764 Y175.186 E.56713
G1 X188.764 Y175.537 E.01128
G1 X190.043 Y170.764 E.15888
G1 X190.135 Y170.764 E.00294
G1 X188.764 Y171.132 E.04562
G1 X188.764 Y171.697 E.01819
G1 X191.313 Y174.28 E.11668
G1 X188.764 Y174.963 E.08485
M204 S10000
G1 X188.764 Y175.741 F60000
G1 F13265.217
M204 S8000
G1 X188.764 Y176.24 E.01606
G1 X191.281 Y175.566 E.08377
G1 X191.292 Y175.638 E.00234
G1 X188.764 Y185.18 E.31741
G1 X201.236 Y181.838 E.41517
M204 S10000
G1 X201.236 Y182.424 F60000
M73 P47 R8
G1 F13265.217
M204 S8000
G1 X196.993 Y178.191 E.19271
G1 X193.777 Y190.192 E.39951
G1 X200.192 Y188.503 E.21331
G1 X200.192 Y188.358 E.00465
G1 X188.764 Y176.931 E.51968
G1 X188.764 Y177.517 E.01885
G1 X191.663 Y176.74 E.09648
G3 X191.39 Y176.067 I4.014 J-2.019 E.02339
G1 X188.764 Y173.442 E.11938
G1 X188.764 Y173.686 E.00785
G1 X191.919 Y172.841 E.10502
G1 X191.811 Y172.999 E.00618
G1 X189.576 Y170.764 E.10163
; WIPE_START
G1 X190.283 Y171.472 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I-.923 J-.793 P1  F60000
G1 X188.764 Y173.238 Z2
G1 Z1.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X188.764 Y172.409 E.02668
G1 X194.901 Y170.764 E.20429
G1 X194.81 Y170.764 E.00293
G1 X195.29 Y171.245 E.02185
G2 X195.025 Y171.237 I-.17 J1.321 E.00855
G1 X195.152 Y170.764 E.01575
G1 X196.225 Y170.764 E.03452
; WIPE_START
G1 X195.225 Y170.764 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I0 J-1.217 P1  F60000
G1 X193.875 Y170.764 Z2
G1 Z1.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X193.684 Y171.475 E.02366
G1 X193.75 Y171.449 E.00228
G1 X193.065 Y170.764 E.03114
G1 X192.597 Y170.764 E.01504
G1 X192.107 Y172.595 E.06095
G3 X192.633 Y172.076 I2.906 J2.417 E.02379
G1 X191.32 Y170.764 E.05966
G1 X188.764 Y180.42 E.32118
G1 X198.537 Y190.192 E.4444
G1 X200.192 Y189.78 E.05486
G1 X200.192 Y188.707 E.03452
M204 S10000
G1 X201.134 Y188.648 F60000
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.53526
G1 F10968.03
M204 S8000
G1 X201.134 Y188.402 E.00957
G1 X200.642 Y188.402 E.01915
G1 X200.642 Y190.303 E.07394
; LINE_WIDTH: 0.51149
G1 F11524.426
G1 X200.589 Y190.373 E.00325
; LINE_WIDTH: 0.482418
G1 F12000
G1 X200.536 Y190.443 E.00305
G1 X200.303 Y190.642 E.01063
; LINE_WIDTH: 0.53532
G1 F10966.704
G1 X189.697 Y190.642 E.41252
G1 X189.36 Y190.346 E.01745
G1 X189.358 Y188.402 E.07562
G1 X188.866 Y188.402 E.01915
G1 X188.866 Y190.303 E.07395
; LINE_WIDTH: 0.516049
G1 F11413.395
G1 X188.847 Y190.599 E.0111
; LINE_WIDTH: 0.477625
G1 F12000
G1 X188.827 Y190.895 E.0102
; LINE_WIDTH: 0.427323
G1 X188.808 Y191.192 E.00902
G1 X189.289 Y191.192 E.0146
; LINE_WIDTH: 0.439202
G1 X189.425 Y191.173 E.0043
; LINE_WIDTH: 0.477625
G1 X189.561 Y191.153 E.00472
; LINE_WIDTH: 0.535015
G1 F10973.503
G1 X189.697 Y191.134 E.00534
G1 X200.303 Y191.134 E.41227
; LINE_WIDTH: 0.516049
G1 F11413.395
G1 X200.599 Y191.153 E.0111
; LINE_WIDTH: 0.477625
G1 F12000
G1 X200.895 Y191.173 E.0102
; LINE_WIDTH: 0.433565
G1 X201.192 Y191.192 E.00916
G1 X201.182 Y190.711 E.01485
; LINE_WIDTH: 0.46395
G1 X201.158 Y190.507 E.00683
; LINE_WIDTH: 0.53255
G1 F11028.751
G1 X201.134 Y190.303 E.00794
G1 X201.134 Y188.708 E.06169
; WIPE_START
G1 X201.134 Y189.708 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I-1.158 J-.374 P1  F60000
G1 X200.805 Y190.727 Z2
G1 Z1.6
G1 E.4 F1800
; LINE_WIDTH: 0.49672
G1 F11899.515
M204 S8000
G2 X200.801 Y190.825 I-.028 J.048 E.0083
; WIPE_START
G1 X200.748 Y190.825 E-.09081
G1 X200.72 Y190.776 E-.0964
G1 X200.748 Y190.727 E-.0964
G1 X200.805 Y190.727 E-.0964
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I0 J-1.217 P1  F60000
G1 X189.252 Y190.727 Z2
G1 Z1.6
G1 E.4 F1800
; LINE_WIDTH: 0.4967
G1 F11900.039
M204 S8000
G2 X189.249 Y190.825 I-.028 J.048 E.0083
; OBJECT_ID: 12
; COOLING_NODE: 0
; WIPE_START
G1 X189.195 Y190.825 E-.09082
G1 X189.167 Y190.776 E-.09639
G1 X189.195 Y190.727 E-.09639
G1 X189.252 Y190.727 E-.09639
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 16
M625
; start printing object, unique label id: 12
M624 AgAAAAAAAAA=
M204 S10000
G17
G3 Z2 I1.209 J.136 P1  F60000
G1 X197.495 Y117.332 Z2
G1 Z1.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X197.447 Y117.381 E.00221
G3 X194.575 Y111.609 I-2.447 J-2.383 E.41911
G1 X194.915 Y111.583 E.01096
G3 X197.62 Y117.19 I.085 J3.415 E.25179
G1 X197.535 Y117.286 E.00414
; COOLING_NODE: 0
M204 S10000
G1 X197.218 Y117.024 F60000
G1 F13265.217
M204 S8000
G1 X197.156 Y117.097 E.00307
G3 X194.626 Y112.013 I-2.156 J-2.099 E.36914
G1 X194.925 Y111.991 E.00965
G3 X197.485 Y116.694 I.075 J3.008 E.21231
G1 X197.255 Y116.978 E.01174
; COOLING_NODE: 0
M204 S10000
G1 X196.904 Y116.767 F60000
G1 F13265.217
M204 S8000
G1 X196.864 Y116.813 E.00197
G3 X194.676 Y112.417 I-1.864 J-1.814 E.31916
G1 X194.935 Y112.398 E.00835
G3 X197.148 Y116.465 I.065 J2.6 E.18356
G1 X196.942 Y116.72 E.01057
; COOLING_NODE: 0
M204 S250
G1 X196.602 Y116.519 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X196.583 Y116.539 E.00083
G3 X194.725 Y112.807 I-1.583 J-1.541 E.25106
G1 X194.945 Y112.79 E.00657
G3 X196.824 Y116.244 I.055 J2.208 E.14439
G1 X196.64 Y116.472 E.00875
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X196.583 Y116.539 E-.03342
G1 X196.29 Y116.795 E-.14757
G1 X195.909 Y117.015 E-.16727
G1 X195.83 Y117.041 E-.03174
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I-1.132 J.448 P1  F60000
G1 X201.584 Y131.584 Z2
G1 Z1.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y131.584 E.42342
G1 X188.416 Y110.416 E.68067
G1 X201.584 Y110.416 E.42342
G1 X201.584 Y131.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y131.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y131.991 E.4496
G1 X188.009 Y110.009 E.70685
G1 X201.991 Y110.009 E.4496
G1 X201.991 Y131.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y132.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y132.398 E.47578
G1 X187.602 Y109.602 E.73303
G1 X202.398 Y109.602 E.47578
G1 X202.398 Y132.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y132.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y132.79 E.46408
G1 X187.21 Y109.21 E.70237
G1 X202.79 Y109.21 E.46408
G1 X202.79 Y132.73 E.70058
; WIPE_START
M204 S8000
G1 X201.79 Y132.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I.949 J-.761 P1  F60000
G1 X199.751 Y130.192 Z2
G1 Z1.6
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X200.163 Y130.192 E.01323
G1 X200.192 Y130.082 E.00365
G1 X188.764 Y118.675 E.51921
G1 X188.764 Y118.794 E.00382
G1 X192.484 Y117.797 E.12384
G3 X192.097 Y117.398 I3.25 J-3.54 E.0179
G1 X189.269 Y127.952 E.35135
G1 X189.318 Y127.952 E.00158
G1 X188.764 Y127.398 E.02519
G1 X188.764 Y127.734 E.01079
G1 X201.236 Y124.392 E.41517
G1 X201.236 Y124.168 E.0072
G1 X195.754 Y118.687 E.24927
G1 X195.574 Y118.719 E.00587
G1 X192.5 Y130.192 E.38196
G1 X193.303 Y130.192 E.02582
G1 X188.764 Y125.654 E.20639
G1 X188.764 Y126.457 E.02583
G1 X201.236 Y123.115 E.41517
G1 X201.236 Y123.965 E.02733
; WIPE_START
G1 X201.236 Y123.115 E-.32292
G1 X201.09 Y123.154 E-.05708
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I1.214 J.078 P1  F60000
G1 X201.236 Y120.883 Z2
G1 Z1.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X201.236 Y121.422 E.01734
G1 X198.858 Y130.192 E.29219
M204 S10000
G1 X198.333 Y130.192 F60000
G1 F13265.217
M204 S8000
G1 X197.609 Y130.192 E.0233
G1 X201.236 Y116.656 E.45063
G1 X201.236 Y116.73 E.00237
G1 X197.613 Y117.7 E.1206
G2 X197.925 Y117.369 I-1.166 J-1.411 E.01468
G1 X201.236 Y120.679 E.15055
G1 X201.236 Y120.561 E.00381
G1 X188.764 Y123.902 E.41517
M204 S10000
G1 X188.764 Y123.909 F60000
G1 F13265.217
M204 S8000
G1 X195.048 Y130.192 E.28573
M204 S10000
G1 X195.054 Y130.192 F60000
G1 F13265.217
M204 S8000
G1 X200.26 Y110.764 E.64676
G1 X200.043 Y110.764 E.00696
G1 X201.236 Y111.957 E.05422
G1 X201.236 Y111.89 E.00215
G1 X196.331 Y130.192 E.6093
G1 X196.792 Y130.192 E.01481
G1 X188.764 Y122.164 E.36506
G1 X188.764 Y122.625 E.01482
G1 X201.236 Y119.284 E.41517
G1 X201.236 Y118.935 E.01122
G1 X198.549 Y116.248 E.12217
M204 S10000
G1 X198.58 Y116.164 F60000
G1 F13265.217
M204 S8000
G1 X201.236 Y115.446 E.08847
G1 X196.554 Y110.764 E.21288
G1 X196.429 Y110.764 E.00404
G1 X196.245 Y111.45 E.02281
G3 X196.588 Y111.589 I-.527 J1.784 E.01193
G1 X199.667 Y110.764 E.1025
G1 X199.271 Y110.764 E.01275
M204 S10000
G1 X198.983 Y110.764 F60000
G1 F13265.217
M204 S8000
G1 X198.323 Y113.229 E.08204
G3 X198.505 Y113.63 I-1.909 J1.109 E.01419
G1 X201.236 Y112.898 E.09091
; WIPE_START
G1 X200.27 Y113.157 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I1.213 J.099 P1  F60000
G1 X200.464 Y110.764 Z2
G1 Z1.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X201.236 Y110.764 E.02481
G1 X201.236 Y111.621 E.02755
G1 X197.841 Y112.531 E.11301
G2 X197.358 Y112.063 I-2.583 J2.186 E.02166
G1 X197.706 Y110.764 E.04324
G1 X198.299 Y110.764 E.01907
G1 X201.236 Y113.701 E.13355
G1 X201.236 Y114.175 E.01525
G1 X198.759 Y114.839 E.08246
G1 X198.752 Y114.707 E.00426
G1 X201.236 Y117.19 E.11294
; WIPE_START
G1 X200.528 Y116.483 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I-1.161 J.365 P1  F60000
G1 X201.236 Y118.731 Z2
G1 Z1.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X201.236 Y118.007 E.0233
G1 X188.764 Y121.348 E.41517
G1 X188.764 Y120.623 E.02331
M204 S10000
G1 X188.764 Y120.1 F60000
G1 F13265.217
M204 S8000
G1 X194.076 Y118.648 E.17707
G3 X193.933 Y118.61 I.116 J-.734 E.00478
G1 X201.236 Y125.913 E.3321
G1 X201.236 Y125.669 E.00784
G1 X189.808 Y128.731 E.38043
G1 X189.808 Y128.442 E.00932
G1 X191.558 Y130.192 E.07961
G1 X191.223 Y130.192 E.01078
G1 X194.303 Y118.7 E.3826
G2 X195.373 Y118.745 I.816 J-6.659 E.03448
; WIPE_START
G1 X194.374 Y118.703 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I.293 J-1.181 P1  F60000
G1 X193.74 Y118.545 Z2
G1 Z1.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G3 X193.14 Y118.27 I1.302 J-3.629 E.02123
G1 X189.946 Y130.192 E.39688
G1 X189.808 Y130.192 E.00444
G1 X189.808 Y130.008 E.00591
G1 X201.236 Y126.946 E.38043
M204 S10000
G1 X201.236 Y126.585 F60000
G1 F13265.217
M204 S8000
G1 X201.236 Y126.188 E.01275
G1 X200.763 Y127.952 E.05872
G1 X201.236 Y127.952 E.0152
G1 X201.236 Y127.657 E.00947
G1 X188.764 Y115.186 E.56713
G1 X188.764 Y115.537 E.01128
G1 X190.043 Y110.764 E.15888
G1 X190.135 Y110.764 E.00294
G1 X188.764 Y111.132 E.04562
G1 X188.764 Y111.697 E.01819
G1 X191.304 Y114.282 E.11652
M73 P48 R8
G1 X188.764 Y114.963 E.08453
M204 S10000
G1 X188.764 Y115.741 F60000
G1 F13265.217
M204 S8000
G1 X188.764 Y116.24 E.01606
G1 X191.281 Y115.566 E.08377
G1 X191.292 Y115.638 E.00234
G1 X188.764 Y125.18 E.31741
G1 X201.236 Y121.838 E.41517
M204 S10000
G1 X201.236 Y122.424 F60000
G1 F13265.217
M204 S8000
G1 X196.993 Y118.191 E.19271
G1 X193.777 Y130.192 E.39951
G1 X200.192 Y128.503 E.21331
G1 X200.192 Y128.358 E.00465
G1 X188.764 Y116.931 E.51968
G1 X188.764 Y117.517 E.01885
G1 X191.663 Y116.74 E.09649
G3 X191.39 Y116.067 I4.001 J-2.014 E.02339
G1 X188.764 Y113.442 E.11938
G1 X188.764 Y113.686 E.00785
G1 X191.916 Y112.841 E.10491
G2 X191.813 Y113.001 I.746 J.594 E.00612
G1 X189.576 Y110.764 E.10171
; WIPE_START
G1 X190.283 Y111.472 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I-.923 J-.793 P1  F60000
G1 X188.764 Y113.238 Z2
G1 Z1.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X188.764 Y112.409 E.02668
G1 X194.901 Y110.764 E.20429
G1 X194.81 Y110.764 E.00293
G1 X195.29 Y111.245 E.02185
G2 X195.025 Y111.237 I-.17 J1.315 E.00855
G1 X195.152 Y110.764 E.01575
G1 X196.225 Y110.764 E.03452
; WIPE_START
G1 X195.225 Y110.764 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I0 J-1.217 P1  F60000
G1 X193.875 Y110.764 Z2
G1 Z1.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X193.684 Y111.475 E.02366
G1 X193.75 Y111.449 E.00228
G1 X193.065 Y110.764 E.03114
G1 X192.597 Y110.764 E.01504
G1 X192.109 Y112.586 E.06063
G3 X192.633 Y112.076 I5.609 J5.237 E.02348
G1 X191.32 Y110.764 E.05966
G1 X188.764 Y120.42 E.32118
G1 X198.537 Y130.192 E.4444
G1 X200.192 Y129.78 E.05486
G1 X200.192 Y128.707 E.03452
M204 S10000
G1 X201.134 Y128.648 F60000
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.53526
G1 F10968.03
M204 S8000
G1 X201.134 Y128.402 E.00957
G1 X200.642 Y128.402 E.01915
G1 X200.642 Y130.303 E.07394
; LINE_WIDTH: 0.51149
G1 F11524.426
G1 X200.589 Y130.373 E.00325
; LINE_WIDTH: 0.482418
G1 F12000
G1 X200.536 Y130.443 E.00305
G1 X200.303 Y130.642 E.01063
; LINE_WIDTH: 0.53532
G1 F10966.704
G1 X189.697 Y130.642 E.41252
G1 X189.36 Y130.346 E.01745
G1 X189.358 Y128.402 E.07562
G1 X188.866 Y128.402 E.01915
G1 X188.866 Y130.303 E.07395
; LINE_WIDTH: 0.516049
G1 F11413.395
G1 X188.847 Y130.599 E.0111
; LINE_WIDTH: 0.477625
G1 F12000
G1 X188.827 Y130.895 E.0102
; LINE_WIDTH: 0.427323
G1 X188.808 Y131.192 E.00902
G1 X189.289 Y131.192 E.0146
; LINE_WIDTH: 0.439202
G1 X189.425 Y131.173 E.0043
; LINE_WIDTH: 0.477625
G1 X189.561 Y131.153 E.00472
; LINE_WIDTH: 0.535015
G1 F10973.503
G1 X189.697 Y131.134 E.00534
G1 X200.303 Y131.134 E.41227
; LINE_WIDTH: 0.516049
G1 F11413.395
G1 X200.599 Y131.153 E.0111
; LINE_WIDTH: 0.477625
G1 F12000
G1 X200.895 Y131.173 E.0102
; LINE_WIDTH: 0.433565
G1 X201.192 Y131.192 E.00916
G1 X201.182 Y130.711 E.01485
; LINE_WIDTH: 0.46395
G1 X201.158 Y130.507 E.00683
; LINE_WIDTH: 0.53255
G1 F11028.751
G1 X201.134 Y130.303 E.00794
G1 X201.134 Y128.708 E.06169
; WIPE_START
G1 X201.134 Y129.708 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I-1.158 J-.374 P1  F60000
G1 X200.805 Y130.727 Z2
G1 Z1.6
G1 E.4 F1800
; LINE_WIDTH: 0.49672
G1 F11899.515
M204 S8000
G2 X200.801 Y130.825 I-.028 J.048 E.0083
; WIPE_START
G1 X200.748 Y130.825 E-.09081
G1 X200.72 Y130.776 E-.0964
G1 X200.748 Y130.727 E-.0964
G1 X200.805 Y130.727 E-.0964
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I0 J-1.217 P1  F60000
G1 X189.252 Y130.727 Z2
G1 Z1.6
G1 E.4 F1800
; LINE_WIDTH: 0.4967
G1 F11900.039
M204 S8000
G2 X189.249 Y130.825 I-.028 J.048 E.0083
; OBJECT_ID: 8
; COOLING_NODE: 0
; WIPE_START
G1 X189.195 Y130.825 E-.09082
G1 X189.167 Y130.776 E-.09639
G1 X189.195 Y130.727 E-.09639
G1 X189.252 Y130.727 E-.09639
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 12
M625
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z2 I.366 J-1.161 P1  F60000
G1 X141.545 Y115.684 Z2
G1 Z1.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X141.545 Y173.92 E1.87265
G1 X140.455 Y173.92 E.03507
G1 X140.455 Y115.684 E1.87265
G1 X121.016 Y115.684 E.62508
G1 X121.016 Y113.516 E.0697
G1 X157.584 Y113.516 E1.17589
G1 X157.584 Y115.684 E.0697
G1 X155.545 Y115.684 E.06555
G1 X155.545 Y173.92 E1.87265
G1 X154.455 Y173.92 E.03507
G1 X154.455 Y115.684 E1.87265
G1 X141.605 Y115.684 E.41319
; COOLING_NODE: 0
M204 S10000
G1 X141.952 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X141.952 Y174.327 E1.87265
G1 X140.048 Y174.327 E.06125
G1 X140.048 Y116.091 E1.87265
G1 X120.609 Y116.091 E.62508
G1 X120.609 Y113.109 E.09588
G1 X157.991 Y113.109 E1.20207
G1 X157.991 Y116.091 E.09588
G1 X155.952 Y116.091 E.06555
G1 X155.952 Y174.327 E1.87265
G1 X154.048 Y174.327 E.06125
G1 X154.048 Y116.091 E1.87265
M73 P48 R7
G1 X142.012 Y116.091 E.38701
; COOLING_NODE: 0
M204 S10000
G1 X142.36 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X142.36 Y174.734 E1.87265
G1 X139.64 Y174.734 E.08743
G1 X139.64 Y116.498 E1.87265
G1 X120.202 Y116.498 E.62508
G1 X120.202 Y112.702 E.12206
G1 X158.398 Y112.702 E1.22825
G1 X158.398 Y116.498 E.12206
G1 X156.36 Y116.498 E.06555
G1 X156.36 Y174.734 E1.87265
G1 X153.64 Y174.734 E.08743
G1 X153.64 Y116.498 E1.87265
G1 X142.42 Y116.498 E.36083
; COOLING_NODE: 0
M204 S250
G1 X142.752 Y116.89 F60000
M106 S127.5
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F3311
M204 S5000
G1 X142.752 Y174.51 E1.7163
G1 X143.429 Y174.51 E.02018
G1 X143.429 Y176.09 E.04706
G1 X141.511 Y176.09 E.05714
G1 X141.511 Y185.967 E.29421
G3 X140.489 Y185.967 I-.51 J-1.013 E.03157
G1 X140.489 Y176.09 E.29419
G1 X138.571 Y176.09 E.05714
G1 X138.571 Y174.51 E.04706
M73 P49 R7
G1 X139.248 Y174.51 E.02018
G1 X139.248 Y116.89 E1.7163
G1 X123.1 Y116.89 E.481
G1 X122.7 Y116.89 E.01191
G1 X122.3 Y116.89 E.01191
G1 X121.9 Y116.89 E.01191
G1 X121.5 Y116.89 E.01191
G1 X121.1 Y116.89 E.01191
G1 X120.7 Y116.89 E.01191
G1 X120.3 Y116.89 E.01191
G1 X119.9 Y116.89 E.01191
G1 X119.81 Y116.89 E.0027
M106 S58.65
M106 S127.5
G1 X119.81 Y112.31 E.13642
M106 S58.65
M106 S127.5
G1 X119.9 Y112.31 E.0027
M106 S58.65
G1 X120.3 Y112.31 E.01191
G1 X120.7 Y112.31 E.01191
G1 X121.1 Y112.31 E.01191
G1 X121.5 Y112.31 E.01191
G1 X121.9 Y112.31 E.01191
G1 X122.3 Y112.31 E.01191
G1 X122.7 Y112.31 E.01191
G1 X123.1 Y112.31 E.01191
G1 X158.79 Y112.31 E1.06307
G1 X158.79 Y116.89 E.13642
G1 X156.752 Y116.89 E.06072
G1 X156.752 Y174.51 E1.7163
G1 X157.429 Y174.51 E.02018
G1 X157.429 Y176.09 E.04706
G1 X155.511 Y176.09 E.05714
G1 X155.511 Y185.967 E.29421
G3 X154.489 Y185.967 I-.51 J-1.013 E.03157
G1 X154.489 Y176.09 E.29419
G1 X152.571 Y176.09 E.05714
G1 X152.571 Y174.51 E.04706
G1 X153.248 Y174.51 E.02018
G1 X153.248 Y116.89 E1.7163
G1 X142.812 Y116.89 E.31088
; WIPE_START
G1 F12000
M204 S8000
G1 X142.811 Y117.89 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I1.206 J-.163 P1  F60000
G1 X142.323 Y114.292 Z2
G1 Z1.6
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X142.761 Y114.292 E.01408
G1 X142.333 Y113.864 E.01945
G1 X142.234 Y113.864 E.00319
G1 X142.12 Y114.292 E.01424
G1 X141.22 Y114.292 E.02893
M204 S10000
G1 X140.382 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X140.589 Y113.864 E.00664
G1 X141.016 Y114.292 E.01945
G1 X140.842 Y114.292 E.00559
G1 X140.957 Y113.864 E.01424
G1 X140.779 Y113.864 E.00573
G1 X139.183 Y114.292 E.05313
G1 X139.272 Y114.292 E.00286
G1 X138.844 Y113.864 E.01945
G1 X138.403 Y113.864 E.01419
G1 X138.288 Y114.292 E.01424
G1 X138.979 Y114.292 E.02222
M204 S10000
G1 X139.475 Y114.292 F60000
G1 F13265.217
M204 S8000
G1 X139.565 Y114.292 E.0029
G1 X139.68 Y113.864 E.01424
; WIPE_START
G1 X139.565 Y114.292 E-.31575
G1 X139.475 Y114.292 E-.06425
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I-.758 J.952 P1  F60000
G1 X140.658 Y115.234 Z2
G1 Z1.6
G1 E.4 F1800
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.55014
G1 F10646.269
M204 S8000
G1 X140.744 Y115.249 E.00348
; LINE_WIDTH: 0.5798
G1 F10058.115
G1 X140.829 Y115.264 E.00368
; LINE_WIDTH: 0.573643
G1 F10174.8
G1 X140.829 Y115.307 E.00182
; LINE_WIDTH: 0.531669
G1 F11048.617
G1 X140.829 Y115.35 E.00167
; LINE_WIDTH: 0.489695
G1 F12000
G1 X140.829 Y115.394 E.00153
; LINE_WIDTH: 0.447721
G1 X140.829 Y115.437 E.00138
; LINE_WIDTH: 0.384768
G1 X140.829 Y173.545 E1.56913
G1 X141.171 Y173.545 E.00923
G1 X141.171 Y115.48 E1.56796
; LINE_WIDTH: 0.405747
G1 X141.171 Y115.437 E.00124
; LINE_WIDTH: 0.447721
G1 X141.171 Y115.394 E.00138
; LINE_WIDTH: 0.489695
G1 X141.171 Y115.35 E.00153
; LINE_WIDTH: 0.531669
G1 F11048.617
G1 X141.171 Y115.307 E.00167
; LINE_WIDTH: 0.566703
G1 F10309.619
G1 X141.171 Y115.264 E.00179
G1 X141.342 Y115.234 E.00718
; LINE_WIDTH: 0.535305
G1 F10967.036
G1 X144.267 Y115.234 E.11377
G1 X144.267 Y114.742 E.01915
G1 X141.342 Y114.742 E.11377
; LINE_WIDTH: 0.55014
G1 F10646.269
G1 X141.171 Y114.757 E.00687
; LINE_WIDTH: 0.569914
G1 F10246.812
G3 X140.658 Y114.742 I-.214 J-1.474 E.02146
; LINE_WIDTH: 0.535305
G1 F10967.036
G1 X137.733 Y114.742 E.11377
G1 X137.733 Y115.234 E.01915
G1 X140.598 Y115.234 E.11143
; WIPE_START
G1 X139.598 Y115.234 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I.188 J1.202 P1  F60000
G1 X144.632 Y114.448 Z2
G1 Z1.6
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X144.788 Y113.864 E.01944
M204 S10000
G1 X145.148 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X145.545 Y113.864 E.01275
G1 X143.949 Y114.292 E.05313
G1 X143.397 Y114.292 E.01776
G1 X143.511 Y113.864 E.01424
G1 X144.078 Y113.864 E.01822
G1 X145.549 Y115.336 E.0669
M204 S10000
G1 X145.671 Y115.336 F60000
G1 F13265.217
M204 S8000
G1 X146.065 Y113.864 E.04897
G1 X145.822 Y113.864 E.00782
G1 X147.293 Y115.336 E.0669
G1 X146.948 Y115.336 E.0111
G1 X147.342 Y113.864 E.04897
G1 X147.567 Y113.864 E.00721
G1 X149.038 Y115.336 E.0669
G1 X148.225 Y115.336 E.02613
G1 X148.62 Y113.864 E.04897
G1 X147.77 Y113.864 E.02731
; WIPE_START
G1 X148.62 Y113.864 E-.3227
G1 X148.581 Y114.01 E-.0573
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I.238 J1.193 P1  F60000
G1 X149.311 Y113.864 Z2
G1 Z1.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X150.782 Y115.336 E.0669
M204 S10000
G1 X150.78 Y115.336 F60000
G1 F13265.217
M204 S8000
G1 X151.174 Y113.864 E.04897
G1 X151.056 Y113.864 E.00379
G1 X151.504 Y114.313 E.02038
G1 X152.336 Y114.292 E.02677
G1 X152.451 Y113.864 E.01424
G1 X152.8 Y113.864 E.01124
G1 X153.228 Y114.292 E.01945
G1 X152.54 Y114.292 E.02213
M204 S10000
G1 X153.004 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X153.728 Y113.864 E.02328
G1 X153.613 Y114.292 E.01424
G1 X153.481 Y114.292 E.00424
G1 X155.077 Y113.864 E.05313
G1 X155.005 Y113.864 E.00232
G1 X154.89 Y114.292 E.01424
G1 X154.973 Y114.292 E.00264
G1 X154.545 Y113.864 E.01945
M204 S10000
G1 X155.176 Y114.292 F60000
G1 F13265.217
M204 S8000
G1 X156.167 Y114.292 E.03188
G1 X156.289 Y113.864 E.0143
G1 X156.717 Y114.292 E.01945
G1 X157.236 Y114.292 E.01667
G1 X157.236 Y113.864 E.01375
G1 X156.553 Y113.864 E.02194
; WIPE_START
G1 X157.236 Y113.864 E-.25925
G1 X157.236 Y114.182 E-.12075
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I-.46 J-1.127 P1  F60000
G1 X154.658 Y115.234 Z2
G1 Z1.6
G1 E.4 F1800
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.55014
G1 F10646.269
M204 S8000
G1 X154.744 Y115.249 E.00348
; LINE_WIDTH: 0.5798
G1 F10058.115
G1 X154.829 Y115.264 E.00368
; LINE_WIDTH: 0.573643
G1 F10174.8
G1 X154.829 Y115.307 E.00182
; LINE_WIDTH: 0.531669
G1 F11048.617
G1 X154.829 Y115.35 E.00167
; LINE_WIDTH: 0.489695
G1 F12000
G1 X154.829 Y115.394 E.00153
; LINE_WIDTH: 0.447721
G1 X154.829 Y115.437 E.00138
M106 S127.5
; LINE_WIDTH: 0.384773
G1 X154.829 Y173.545 E1.56915
G1 X155.171 Y173.545 E.00923
G1 X155.171 Y115.48 E1.56798
; LINE_WIDTH: 0.405747
G1 X155.171 Y115.437 E.00124
; LINE_WIDTH: 0.447721
G1 X155.171 Y115.394 E.00138
; LINE_WIDTH: 0.489695
G1 X155.171 Y115.35 E.00153
; LINE_WIDTH: 0.531669
G1 F11048.617
G1 X155.171 Y115.307 E.00167
; LINE_WIDTH: 0.566703
G1 F10309.619
G1 X155.171 Y115.264 E.00179
G1 X155.342 Y115.234 E.00718
; LINE_WIDTH: 0.535305
G1 F10967.04
G1 X157.134 Y115.234 E.06971
G1 X157.134 Y114.742 E.01915
G1 X155.342 Y114.742 E.06971
; LINE_WIDTH: 0.55014
G1 F10646.269
G1 X155.171 Y114.757 E.00687
; LINE_WIDTH: 0.569914
G1 F10246.812
G3 X154.658 Y114.742 I-.214 J-1.474 E.02146
; LINE_WIDTH: 0.535305
G1 F10967.036
G1 X151.733 Y114.742 E.11377
G1 X151.733 Y115.234 E.01915
G1 X154.598 Y115.234 E.11143
; WIPE_START
G1 X153.598 Y115.234 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I-.047 J-1.216 P1  F60000
G1 X150.986 Y115.336 Z2
G1 Z1.6
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X151.284 Y115.336 E.00957
G1 X151.284 Y114.881 E.01462
G1 X149.502 Y115.336 E.05911
G1 X149.897 Y113.864 E.04897
M204 S10000
G1 X150.852 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X150.311 Y113.864 E.0174
G1 X144.821 Y115.336 E.18277
G1 X144.716 Y115.336 E.00336
G1 X144.716 Y114.964 E.01196
; WIPE_START
G1 X144.716 Y115.336 E-.14128
G1 X144.821 Y115.336 E-.0397
G1 X145.327 Y115.2 E-.19901
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I.162 J-1.206 P1  F60000
G1 X135.355 Y113.864 Z2
G1 Z1.6
M73 P50 R7
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X136.826 Y115.336 E.0669
G1 X136.732 Y115.336 E.00304
G1 X137.1 Y113.864 E.04876
G1 X137.525 Y114.292 E.01939
G2 X137.284 Y114.801 I.134 J.375 E.02011
G1 X135.289 Y115.336 E.06641
G1 X135.455 Y115.336 E.00533
G1 X135.849 Y113.864 E.04897
G1 X136.013 Y113.864 E.00527
G1 X130.522 Y115.336 E.18277
G1 X130.346 Y115.336 E.00567
G1 X130.74 Y113.864 E.04897
M204 S10000
G1 X130.121 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X131.593 Y115.336 E.0669
M204 S10000
G1 X131.623 Y115.336 F60000
G1 F13265.217
M204 S8000
G1 X132.017 Y113.864 E.04897
G1 X131.866 Y113.864 E.00487
G1 X133.337 Y115.336 E.0669
G1 X132.9 Y115.336 E.01404
G1 X133.295 Y113.864 E.04897
G1 X133.611 Y113.864 E.01016
G1 X135.082 Y115.336 E.0669
G1 X134.177 Y115.336 E.02908
G1 X134.572 Y113.864 E.04897
G1 X133.814 Y113.864 E.02436
; WIPE_START
G1 X134.572 Y113.864 E-.28785
G1 X134.509 Y114.099 E-.09215
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I.1 J-1.213 P1  F60000
G1 X131.662 Y113.864 Z2
G1 Z1.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X131.246 Y113.864 E.01338
G1 X125.756 Y115.336 E.18277
G1 X125.238 Y115.336 E.01667
G1 X125.632 Y113.864 E.04897
; WIPE_START
G1 X125.373 Y114.83 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I-.555 J1.083 P1  F60000
G1 X126.359 Y115.336 Z2
G1 Z1.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X124.888 Y113.864 E.0669
G1 X124.355 Y113.864 E.01714
G1 X123.961 Y115.336 E.04897
G1 X124.614 Y115.336 E.02102
G1 X123.143 Y113.864 E.0669
G1 X123.078 Y113.864 E.00211
G1 X122.684 Y115.336 E.04897
G1 X122.87 Y115.336 E.00599
G1 X121.399 Y113.864 E.0669
G1 X121.801 Y113.864 E.01292
G1 X121.407 Y115.336 E.04897
G1 X121.364 Y115.336 E.00136
G1 X121.364 Y115.235 E.00322
G1 X126.48 Y113.864 E.17032
G1 X126.632 Y113.864 E.00489
G1 X128.104 Y115.336 E.0669
G1 X127.792 Y115.336 E.01002
G1 X128.186 Y113.864 E.04897
G1 X128.377 Y113.864 E.00613
G1 X129.848 Y115.336 E.0669
G1 X129.069 Y115.336 E.02505
G1 X129.463 Y113.864 E.04897
G1 X128.58 Y113.864 E.02839
M204 S10000
G1 X127.983 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X126.909 Y113.864 E.03452
G1 X126.515 Y115.336 E.04897
; WIPE_START
G1 X126.774 Y114.37 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I-1.194 J.237 P1  F60000
G1 X138.767 Y174.818 Z2
G1 Z1.6
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.26666
G1 F15000
M204 S8000
G1 X139.444 Y174.818 E.01197
; WIPE_START
G1 X138.767 Y174.818 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I0 J1.217 P1  F60000
G1 X142.556 Y174.818 Z2
G1 Z1.6
G1 E.4 F1800
G1 F15000
M204 S8000
G1 X143.233 Y174.818 E.01197
; WIPE_START
G1 X142.556 Y174.818 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I0 J1.217 P1  F60000
G1 X152.767 Y174.818 Z2
G1 Z1.6
G1 E.4 F1800
G1 F15000
M204 S8000
G1 X153.444 Y174.818 E.01197
; WIPE_START
G1 X152.767 Y174.818 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I0 J1.217 P1  F60000
G1 X156.556 Y174.818 Z2
G1 Z1.6
G1 E.4 F1800
G1 F15000
M204 S8000
G1 X157.233 Y174.818 E.01197
; WIPE_START
G1 X156.556 Y174.818 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I-1.209 J-.143 P1  F60000
G1 X155.303 Y185.422 Z2
G1 Z1.6
G1 E.4 F1800
; FEATURE: Top surface
; LINE_WIDTH: 0.42
G1 F12000
M204 S2000
G1 X154.857 Y185.868 E.01881
G1 X154.723 Y186.002
G1 X154.563 Y185.629
G1 X154.697 Y185.496
G1 X155.303 Y184.889 E.02556
G1 X155.437 Y184.755
G1 X155.437 Y184.222
G1 X155.303 Y184.355
G1 X154.697 Y184.962 E.02556
G1 X154.563 Y185.096
G1 X154.563 Y184.563
G1 X154.697 Y184.429
G1 X155.303 Y183.822 E.02556
G1 X155.437 Y183.688
G1 X155.437 Y183.155
G1 X155.303 Y183.289
G1 X154.697 Y183.896 E.02556
G1 X154.563 Y184.029
G1 X154.563 Y183.496
G1 X154.697 Y183.362
G1 X155.303 Y182.756 E.02556
G1 X155.437 Y182.622
G1 X155.437 Y182.089
G1 X155.303 Y182.222
G1 X154.697 Y182.829 E.02556
G1 X154.563 Y182.963
G1 X154.563 Y182.43
G1 X154.697 Y182.296
G1 X155.303 Y181.689 E.02556
G1 X155.437 Y181.555
G1 X155.437 Y181.022
G1 X155.303 Y181.156
G1 X154.697 Y181.763 E.02556
G1 X154.563 Y181.896
G1 X154.563 Y181.363
G1 X154.697 Y181.229
G1 X155.303 Y180.623 E.02556
G1 X155.437 Y180.489
G1 X155.437 Y179.956
G1 X155.303 Y180.089
G1 X154.697 Y180.696 E.02556
G1 X154.563 Y180.83
G1 X154.563 Y180.297
G1 X154.697 Y180.163
G1 X155.303 Y179.556 E.02556
G1 X155.437 Y179.422
G1 X155.437 Y178.889
G1 X155.303 Y179.023
G1 X154.697 Y179.63 E.02556
G1 X154.563 Y179.763
G1 X154.563 Y179.23
G1 X154.697 Y179.096
G1 X155.303 Y178.49 E.02556
G1 X155.437 Y178.356
G1 X155.437 Y177.823
G1 X155.303 Y177.956
G1 X154.697 Y178.563 E.02556
G1 X154.563 Y178.697
G1 X154.563 Y178.164
G1 X154.697 Y178.03
G1 X155.303 Y177.423 E.02556
G1 X155.437 Y177.289
G1 X155.437 Y176.756
G1 X155.303 Y176.89
G1 X154.697 Y177.497 E.02556
G1 X154.563 Y177.63
G1 X154.563 Y177.097
G1 X154.697 Y176.963
G1 X155.303 Y176.357 E.02556
; WIPE_START
M204 S8000
G1 X154.697 Y176.963 E-.32612
G1 X154.596 Y177.064 E-.05388
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I.566 J1.077 P1  F60000
G1 X156.844 Y175.883 Z2
G1 Z1.6
G1 E.4 F1800
G1 F12000
M204 S2000
G1 X157.222 Y175.505 E.01592
G1 X157.355 Y175.371
G1 X157.355 Y174.838
G1 X157.222 Y174.971
G1 X156.311 Y175.883 E.03838
G1 X156.177 Y176.016
G1 X155.644 Y176.016
G1 X155.777 Y175.883
G1 X156.704 Y174.956 E.03902
G1 X156.837 Y174.823
G1 X156.304 Y174.823
G1 X156.17 Y174.956
G1 X154.697 Y176.43 E.06209
G1 X154.563 Y176.564
G1 X154.563 Y176.031
G1 X154.697 Y175.897
G1 X155.637 Y174.956 E.03962
G1 X155.771 Y174.823
G1 X155.238 Y174.823
G1 X155.104 Y174.956
G1 X154.178 Y175.883 E.03902
G1 X154.044 Y176.016
G1 X153.511 Y176.016
G1 X153.644 Y175.883
G1 X154.571 Y174.956 E.03902
G1 X154.704 Y174.823
G1 X154.171 Y174.823
G1 X154.037 Y174.956
G1 X153.111 Y175.883 E.03902
G1 X152.977 Y176.016
G1 X152.645 Y175.816
G1 X152.778 Y175.682
G1 X153.504 Y174.956 E.03058
; WIPE_START
M204 S8000
G1 X152.797 Y175.663 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I-.768 J-.944 P1  F60000
G1 X141.303 Y185.024 Z2
G1 Z1.6
G1 E.4 F1800
G1 F12000
M204 S2000
G1 X140.697 Y185.631 E.02556
G1 X140.563 Y185.764
G1 X140.563 Y185.231
G1 X140.697 Y185.098
G1 X141.303 Y184.491 E.02556
G1 X141.437 Y184.357
G1 X141.437 Y183.824
G1 X141.303 Y183.957
G1 X140.697 Y184.564 E.02556
G1 X140.563 Y184.698
G1 X140.563 Y184.165
G1 X140.697 Y184.031
G1 X141.303 Y183.424 E.02556
G1 X141.437 Y183.291
G1 X141.437 Y182.757
G1 X141.303 Y182.891
G1 X140.697 Y183.498 E.02556
G1 X140.563 Y183.631
G1 X140.563 Y183.098
G1 X140.697 Y182.965
G1 X141.303 Y182.358 E.02556
G1 X141.437 Y182.224
G1 X141.437 Y181.691
G1 X141.303 Y181.824
G1 X140.697 Y182.431 E.02556
G1 X140.563 Y182.565
G1 X140.563 Y182.032
G1 X140.697 Y181.898
G1 X141.303 Y181.291 E.02556
G1 X141.437 Y181.158
G1 X141.437 Y180.624
G1 X141.303 Y180.758
G1 X140.697 Y181.365 E.02556
G1 X140.563 Y181.498
G1 X140.563 Y180.965
G1 X140.697 Y180.831
G1 X141.303 Y180.225 E.02556
G1 X141.437 Y180.091
G1 X141.437 Y179.558
G1 X141.303 Y179.691
G1 X140.697 Y180.298 E.02556
G1 X140.563 Y180.432
G1 X140.563 Y179.899
G1 X140.697 Y179.765
G1 X141.303 Y179.158 E.02556
G1 X141.437 Y179.024
G1 X141.437 Y178.491
G1 X141.303 Y178.625
G1 X140.697 Y179.232 E.02556
G1 X140.563 Y179.365
G1 X140.563 Y178.832
G1 X140.697 Y178.698
G1 X141.303 Y178.092 E.02556
G1 X141.437 Y177.958
G1 X141.437 Y177.425
G1 X141.303 Y177.558
G1 X140.697 Y178.165 E.02556
G1 X140.563 Y178.299
G1 X140.563 Y177.766
G1 X140.697 Y177.632
G1 X141.303 Y177.025 E.02556
G1 X141.437 Y176.891
G1 X141.437 Y176.358
G1 X141.303 Y176.492
G1 X140.697 Y177.099 E.02556
G1 X140.563 Y177.232
G1 X140.563 Y176.699
G1 X140.697 Y176.565
G1 X141.303 Y175.959 E.02556
G1 X141.437 Y175.825
G1 X142.312 Y176.016
G1 X142.446 Y175.883
G1 X143.222 Y175.107 E.03268
G1 X143.355 Y174.973
G1 X142.973 Y174.823
G1 X142.839 Y174.956
G1 X141.913 Y175.883 E.03902
G1 X141.779 Y176.016
G1 X141.246 Y176.016
G1 X141.379 Y175.883
G1 X142.306 Y174.956 E.03902
G1 X142.439 Y174.823
G1 X141.906 Y174.823
G1 X141.773 Y174.956
G1 X140.697 Y176.032 E.04532
G1 X140.563 Y176.166
G1 X140.179 Y176.016
G1 X140.313 Y175.883
G1 X141.239 Y174.956 E.03902
G1 X141.373 Y174.823
G1 X140.84 Y174.823
G1 X140.706 Y174.956
G1 X139.78 Y175.883 E.03902
G1 X139.646 Y176.016
G1 X139.113 Y176.016
G1 X139.246 Y175.883
G1 X140.173 Y174.956 E.03902
G1 X140.306 Y174.823
G1 X139.773 Y174.823
G1 X139.639 Y174.956
G1 X138.778 Y175.817 E.03628
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X139.485 Y175.11 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I1.125 J-.464 P1  F60000
G1 X114.984 Y115.684 Z2
G1 Z1.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X112.416 Y115.684 E.08257
G1 X112.416 Y113.516 E.0697
G1 X114.984 Y113.516 E.08257
G1 X114.984 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X115.391 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X112.009 Y116.091 E.10875
G1 X112.009 Y113.109 E.09588
G1 X115.391 Y113.109 E.10875
G1 X115.391 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X115.798 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X111.602 Y116.498 E.13493
G1 X111.602 Y112.702 E.12206
G1 X115.798 Y112.702 E.13493
G1 X115.798 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X116.1 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F3311
M204 S5000
G1 X111.21 Y116.89 E.14565
G1 X111.21 Y112.31 E.13642
G1 X112.9 Y112.31 E.05033
G1 X113.3 Y112.31 E.01191
G1 X113.7 Y112.31 E.01191
G1 X114.1 Y112.31 E.01191
G1 X114.5 Y112.31 E.01191
G1 X114.9 Y112.31 E.01191
G1 X115.3 Y112.31 E.01191
G1 X115.7 Y112.31 E.01191
G1 X116.1 Y112.31 E.01191
G1 X116.19 Y112.31 E.0027
M106 S58.65
M106 S127.5
G1 X116.19 Y116.89 E.13642
M106 S58.65
M106 S127.5
G1 X116.16 Y116.89 E.00091
M106 S58.65
; WIPE_START
G1 F3959.375
M204 S8000
G1 X115.16 Y116.89 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2 I1.147 J-.407 P1  F60000
G1 X114.592 Y115.292 Z2
G1 Z1.6
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X114.592 Y113.908 E.04121
G1 X112.808 Y113.908 E.05313
G1 X112.808 Y115.292 E.04121
G1 X114.532 Y115.292 E.05134
M204 S10000
G1 X114.152 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X114.152 Y114.348 E.02
G1 X113.248 Y114.348 E.03591
G1 X113.248 Y114.852 E.02
G1 X114.092 Y114.852 E.03353
; CHANGE_LAYER
; Z_HEIGHT: 1.8
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F10731.32
G1 X113.248 Y114.852 E-.3205
G1 X113.248 Y114.695 E-.0595
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 9/27
; update layer progress
M73 L9
M991 S0 P8 ;notify layer change
M106 S61.2
; OBJECT_ID: 16
; COOLING_NODE: 0
; start printing object, unique label id: 16
M624 BAAAAAAAAAA=
M204 S10000
G17
G3 Z2 I-.747 J.961 P1  F60000
G1 X195.182 Y178.41 Z2
G1 Z1.8
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X195.085 Y178.414 E.00313
G3 X194.575 Y171.609 I-.085 J-3.415 E.33417
G1 X194.915 Y171.583 E.01097
G3 X195.425 Y178.388 I.085 J3.415 E.33417
G1 X195.242 Y178.404 E.00589
; COOLING_NODE: 0
M204 S10000
G1 X195.152 Y178.004 F60000
G1 F13265.217
M204 S8000
G1 X195.075 Y178.007 E.00248
G3 X194.626 Y172.013 I-.075 J-3.008 E.29434
G1 X194.925 Y171.991 E.00966
G3 X195.374 Y177.985 I.075 J3.008 E.29434
G1 X195.212 Y177.999 E.00524
; COOLING_NODE: 0
M204 S10000
G1 X195.121 Y177.598 F60000
G1 F13265.217
M204 S8000
G1 X195.065 Y177.601 E.00182
G3 X194.676 Y172.417 I-.065 J-2.601 E.25453
G1 X194.935 Y172.398 E.00835
G3 X195.324 Y177.581 I.065 J2.601 E.25453
G1 X195.181 Y177.593 E.00459
; COOLING_NODE: 0
M204 S250
G1 X195.091 Y177.205 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X195.055 Y177.199 E.00111
G3 X194.725 Y172.807 I-.055 J-2.204 E.19976
G1 X194.945 Y172.79 E.00657
G3 X195.489 Y177.144 I.055 J2.204 E.19323
G1 X195.151 Y177.196 E.01021
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X195.055 Y177.199 E-.03649
G1 X194.619 Y177.177 E-.16586
G1 X194.192 Y177.057 E-.16831
G1 X194.171 Y177.046 E-.00934
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-1.084 J.553 P1  F60000
G1 X201.584 Y191.584 Z2.2
G1 Z1.8
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y191.584 E.42342
G1 X188.416 Y170.416 E.68067
G1 X201.584 Y170.416 E.42342
G1 X201.584 Y191.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y191.991 F60000
G1 F13265.217
M204 S8000
M73 P51 R7
G1 X188.009 Y191.991 E.4496
G1 X188.009 Y170.009 E.70685
G1 X201.991 Y170.009 E.4496
G1 X201.991 Y191.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y192.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y192.398 E.47578
G1 X187.602 Y169.602 E.73303
G1 X202.398 Y169.602 E.47578
G1 X202.398 Y192.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y192.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y192.79 E.46408
G1 X187.21 Y169.21 E.70237
G1 X202.79 Y169.21 E.46408
G1 X202.79 Y192.73 E.70058
; object ids of layer 9 start: 8,12,16
M624 BwAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer9 end: 8,12,16
M625
; WIPE_START
M204 S8000
G1 X201.79 Y192.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I1.202 J-.193 P1  F60000
G1 X201.134 Y188.648 Z2.2
G1 Z1.8
G1 E.4 F1800
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.53526
G1 F10968.03
M204 S8000
G1 X201.134 Y188.402 E.00957
G1 X200.642 Y188.402 E.01915
G1 X200.642 Y190.303 E.07394
; LINE_WIDTH: 0.51149
G1 F11524.426
G1 X200.589 Y190.373 E.00325
; LINE_WIDTH: 0.482418
G1 F12000
G1 X200.536 Y190.443 E.00305
G1 X200.303 Y190.642 E.01063
; LINE_WIDTH: 0.53532
G1 F10966.704
G1 X189.697 Y190.642 E.41252
G1 X189.36 Y190.346 E.01745
G1 X189.358 Y188.402 E.07562
G1 X188.866 Y188.402 E.01915
G1 X188.866 Y190.303 E.07395
; LINE_WIDTH: 0.516049
G1 F11413.395
G1 X188.847 Y190.599 E.0111
; LINE_WIDTH: 0.477625
G1 F12000
G1 X188.827 Y190.895 E.0102
; LINE_WIDTH: 0.427323
G1 X188.808 Y191.192 E.00902
G1 X189.289 Y191.192 E.0146
; LINE_WIDTH: 0.439202
G1 X189.425 Y191.173 E.0043
; LINE_WIDTH: 0.477625
G1 X189.561 Y191.153 E.00472
; LINE_WIDTH: 0.535015
G1 F10973.503
G1 X189.697 Y191.134 E.00534
G1 X200.303 Y191.134 E.41227
; LINE_WIDTH: 0.516049
G1 F11413.395
G1 X200.599 Y191.153 E.0111
; LINE_WIDTH: 0.477625
G1 F12000
G1 X200.895 Y191.173 E.0102
; LINE_WIDTH: 0.433565
G1 X201.192 Y191.192 E.00916
G1 X201.182 Y190.711 E.01485
; LINE_WIDTH: 0.46395
G1 X201.158 Y190.507 E.00683
; LINE_WIDTH: 0.53255
G1 F11028.751
G1 X201.134 Y190.303 E.00794
G1 X201.134 Y188.708 E.06169
; WIPE_START
G1 X201.134 Y189.708 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-1.158 J-.374 P1  F60000
G1 X200.805 Y190.727 Z2.2
G1 Z1.8
G1 E.4 F1800
; LINE_WIDTH: 0.49672
G1 F11899.515
M204 S8000
G2 X200.801 Y190.825 I-.028 J.048 E.0083
; WIPE_START
G1 X200.748 Y190.825 E-.09081
G1 X200.72 Y190.776 E-.0964
G1 X200.748 Y190.727 E-.0964
G1 X200.805 Y190.727 E-.0964
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I0 J-1.217 P1  F60000
G1 X189.252 Y190.727 Z2.2
G1 Z1.8
G1 E.4 F1800
; LINE_WIDTH: 0.4967
G1 F11900.039
M204 S8000
G2 X189.249 Y190.825 I-.028 J.048 E.0083
; WIPE_START
G1 X189.195 Y190.825 E-.09082
G1 X189.167 Y190.776 E-.09639
G1 X189.195 Y190.727 E-.09639
G1 X189.252 Y190.727 E-.09639
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I1.211 J.116 P1  F60000
G1 X189.518 Y187.952 Z2.2
G1 Z1.8
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.764 Y187.198 E.03429
G1 X188.764 Y186.603 E.01913
G1 X201.236 Y183.261 E.41517
G1 X201.236 Y182.224 E.03337
G1 X197.121 Y178.109 E.18713
G2 X197.389 Y177.907 I-.878 J-1.444 E.01082
G1 X201.236 Y176.876 E.12806
M204 S10000
G1 X201.236 Y176.99 F60000
G1 F13265.217
M204 S8000
G1 X198.726 Y174.481 E.11411
G2 X198.553 Y173.763 I-3.789 J.533 E.02377
G1 X201.236 Y173.045 E.08929
G1 X201.236 Y173.501 E.01468
G1 X198.499 Y170.764 E.12445
G1 X198.836 Y170.764 E.01086
G1 X198.222 Y173.058 E.07635
G2 X197.94 Y172.651 I-2.173 J1.204 E.01595
G1 X201.236 Y171.768 E.10971
M204 S10000
G1 X201.236 Y171.757 F60000
G1 F13265.217
M204 S8000
G1 X200.243 Y170.764 E.04512
G1 X196.781 Y171.684 E.1152
G3 X197.235 Y171.974 I-1.218 J2.413 E.01736
G1 X197.559 Y170.764 E.04026
G1 X198.295 Y170.764 E.02366
; WIPE_START
G1 X197.559 Y170.764 E-.27965
G1 X197.491 Y171.02 E-.10035
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I.216 J-1.198 P1  F60000
G1 X196.079 Y170.764 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X195.447 Y170.764 E.0203
G1 X188.764 Y172.555 E.22248
G1 X188.764 Y173.242 E.02208
G1 X191.321 Y175.799 E.11628
M204 S10000
G1 X191.302 Y175.706 F60000
G1 F13265.217
M204 S8000
G1 X188.764 Y176.386 E.08448
G1 X188.764 Y176.731 E.01108
G1 X200.209 Y188.176 E.52047
G1 X200.192 Y188.649 E.01524
G1 X194.435 Y190.192 E.19166
G1 X193.834 Y190.192 E.01931
; WIPE_START
G1 X194.435 Y190.192 E-.22814
G1 X194.821 Y190.089 E-.15186
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-.039 J-1.216 P1  F60000
G1 X191.555 Y190.192 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X191.077 Y190.192 E.01538
G1 X194.165 Y178.666 E.3837
G1 X201.236 Y185.713 E.321
G1 X201.236 Y185.642 E.00229
G1 X200.617 Y187.952 E.07691
G1 X201.236 Y187.952 E.01991
G1 X201.236 Y187.661 E.00936
; WIPE_START
G1 X201.236 Y187.952 E-.11058
G1 X200.617 Y187.952 E-.23523
G1 X200.64 Y187.865 E-.03418
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-1.108 J-.502 P1  F60000
G1 X200.192 Y188.853 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G3 X200.016 Y190.192 I-2.587 J.342 E.04393
G1 X199.201 Y190.192 E.02622
G1 X200.192 Y189.903 E.0332
G1 X188.764 Y178.475 E.51968
G1 X188.764 Y177.663 E.02611
G1 X191.735 Y176.868 E.09888
G2 X191.989 Y177.255 I2.06 J-1.074 E.01493
G1 X189.123 Y187.952 E.3561
G1 X188.764 Y187.952 E.01152
G1 X188.764 Y187.88 E.00231
G1 X201.236 Y184.539 E.41517
G1 X201.236 Y183.968 E.01833
G1 X195.917 Y178.65 E.24186
G3 X195.422 Y178.741 I-1.154 J-4.892 E.01619
G1 X192.354 Y190.192 E.38122
G1 X191.758 Y190.192 E.01914
G1 X189.808 Y188.242 E.0887
G1 X189.808 Y188.878 E.02045
G1 X201.236 Y185.816 E.38043
G1 X201.236 Y186.038 E.00716
; WIPE_START
G1 X201.236 Y185.816 E-.08457
G1 X200.485 Y186.017 E-.29543
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I1.196 J.223 P1  F60000
G1 X201.236 Y181.984 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X188.764 Y185.326 E.41517
G1 X188.764 Y185.454 E.0041
G1 X193.503 Y190.192 E.21549
G1 X193.631 Y190.192 E.00411
G1 X196.819 Y178.295 E.39605
G3 X196.113 Y178.595 I-1.946 J-3.601 E.02468
M204 S10000
G1 X195.219 Y178.756 F60000
G1 F13265.217
M204 S8000
G3 X194.378 Y178.713 I-.217 J-4.03 E.02713
G1 X188.764 Y180.22 E.1869
G1 X198.739 Y190.192 E.45355
G1 X201.236 Y180.876 E.31015
G1 X201.236 Y180.707 E.00541
G1 X188.764 Y184.049 E.41517
M204 S10000
G1 X188.764 Y183.709 F60000
G1 F13265.217
M204 S8000
G1 X195.248 Y190.192 E.29482
M204 S10000
G1 X194.908 Y190.192 F60000
G1 F13265.217
M204 S8000
G1 X200.114 Y170.764 E.64676
G1 X199.817 Y170.764 E.00954
M204 S10000
G1 X200.447 Y170.764 F60000
G1 F13265.217
M204 S8000
G1 X201.236 Y170.764 E.02536
G1 X201.236 Y171.343 E.01861
G1 X196.185 Y190.192 E.62749
G1 X196.789 Y190.192 E.01941
; WIPE_START
G1 X196.185 Y190.192 E-.22933
G1 X196.288 Y189.809 E-.15067
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I1.21 J.126 P1  F60000
G1 X197.543 Y177.775 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G2 X198.014 Y177.258 I-3.372 J-3.544 E.0225
G1 X201.236 Y180.479 E.14651
G1 X201.236 Y179.43 E.03374
G1 X188.764 Y182.772 E.41517
G1 X188.764 Y182.168 E.01942
; WIPE_START
G1 X188.764 Y182.772 E-.22945
G1 X189.147 Y182.669 E-.15056
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-1.202 J-.188 P1  F60000
G1 X188.764 Y185.122 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X188.764 Y184.523 E.01928
G1 X191.246 Y175.26 E.30835
G3 X191.251 Y174.636 I3.117 J-.286 E.0201
M204 S10000
G1 X191.401 Y173.887 F60000
G1 F13265.217
M204 S8000
G3 X191.797 Y173.02 I54.988 J24.562 E.03065
G1 X188.764 Y173.832 E.10096
; WIPE_START
G1 X189.73 Y173.573 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-1.141 J-.422 P1  F60000
G1 X188.764 Y176.183 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X188.764 Y175.109 E.03452
G1 X191.281 Y174.435 E.08377
G3 X191.351 Y174.084 I1.792 J.178 E.01153
G1 X188.764 Y171.497 E.11764
G1 X188.764 Y171.278 E.00705
G1 X190.681 Y170.764 E.06381
G1 X190.97 Y170.764 E.0093
M204 S10000
G1 X191.724 Y170.764 F60000
G1 F13265.217
M204 S8000
G1 X192.451 Y170.764 E.02337
G1 X191.879 Y172.9 E.07108
G1 X189.776 Y170.764 E.09636
M204 S10000
G1 X189.897 Y170.764 F60000
G1 F13265.217
M204 S8000
G1 X188.764 Y174.991 E.14069
G1 X201.236 Y187.457 E.56704
G1 X201.236 Y187.093 E.01173
G1 X189.808 Y190.161 E.38048
G1 X193.014 Y178.195 E.39834
G3 X192.612 Y177.91 I2.414 J-3.828 E.01588
G1 X188.764 Y178.941 E.12808
; WIPE_START
G1 X189.73 Y178.682 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-.985 J-.714 P1  F60000
G1 X188.764 Y180.014 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X188.764 Y179.757 E.00828
G1 X191.174 Y170.764 E.29936
G1 X191.521 Y170.764 E.01115
G1 X192.744 Y171.988 E.05562
G3 X193.165 Y171.713 I2.919 J4.021 E.01618
M204 S10000
G1 X193.52 Y171.539 F60000
G1 F13265.217
M204 S8000
G1 X193.728 Y170.764 E.0258
G1 X193.265 Y170.764 E.01488
G1 X193.902 Y171.401 E.02895
M204 S10000
G1 X194.879 Y171.237 F60000
G1 F13265.217
M204 S8000
G1 X195.005 Y170.764 E.01572
M204 S10000
G1 X195.01 Y170.764 F60000
G1 F13265.217
M204 S8000
G1 X195.519 Y171.274 E.02315
G3 X196.111 Y171.405 I-.57 J3.981 E.01951
G1 X196.282 Y170.764 E.02131
G1 X196.754 Y170.764 E.01518
G1 X201.236 Y175.246 E.20379
G1 X201.236 Y175.599 E.01136
G1 X198.513 Y176.328 E.09062
M204 S10000
G1 X198.602 Y176.101 F60000
G1 F13265.217
M204 S8000
G1 X201.236 Y178.735 E.11978
G1 X201.236 Y178.153 E.0187
G1 X188.764 Y181.495 E.41517
G1 X188.764 Y181.964 E.0151
G1 X196.992 Y190.192 E.37416
G1 X197.462 Y190.192 E.01512
G1 X201.236 Y176.109 E.46882
G1 X201.236 Y175.802 E.00987
M204 S10000
G1 X201.236 Y175.042 F60000
G1 F13265.217
M204 S8000
G1 X201.236 Y174.322 E.02316
G1 X198.766 Y174.984 E.08222
; OBJECT_ID: 12
; COOLING_NODE: 0
; WIPE_START
G1 X199.732 Y174.725 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 16
M625
; start printing object, unique label id: 12
M624 AgAAAAAAAAA=
M204 S10000
G17
G3 Z2.2 I1.216 J-.047 P1  F60000
G1 X197.494 Y117.332 Z2.2
G1 Z1.8
G1 E.4 F1800
; FEATURE: Inner wall
G1 F13265.217
M204 S8000
G1 X197.442 Y117.388 E.00244
G3 X194.575 Y111.609 I-2.442 J-2.389 E.41894
G1 X194.915 Y111.583 E.01096
G3 X197.62 Y117.191 I.085 J3.415 E.25187
G1 X197.534 Y117.288 E.00415
; COOLING_NODE: 0
M204 S10000
G1 X197.193 Y117.058 F60000
G1 F13265.217
M204 S8000
G1 X197.151 Y117.104 E.00201
G3 X194.626 Y112.013 I-2.151 J-2.105 E.36902
G1 X194.925 Y111.991 E.00965
G3 X197.307 Y116.931 I.075 J3.009 E.22188
G1 X197.234 Y117.013 E.00355
; COOLING_NODE: 0
M204 S10000
G1 X196.904 Y116.766 F60000
M73 P52 R7
G1 F13265.217
M204 S8000
G1 X196.86 Y116.819 E.00221
G3 X194.676 Y112.417 I-1.86 J-1.82 E.31907
G1 X194.935 Y112.398 E.00835
G3 X197.15 Y116.466 I.065 J2.601 E.18361
G1 X196.942 Y116.72 E.01057
; COOLING_NODE: 0
M204 S250
G1 X196.602 Y116.518 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X196.573 Y116.539 E.00106
G3 X194.725 Y112.807 I-1.573 J-1.544 E.25031
G1 X194.945 Y112.79 E.00657
G3 X196.819 Y116.24 I.055 J2.204 E.14421
G1 X196.639 Y116.471 E.00872
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X196.573 Y116.539 E-.03598
G1 X196.29 Y116.795 E-.14485
G1 X195.909 Y117.015 E-.16731
G1 X195.83 Y117.041 E-.03186
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-1.132 J.448 P1  F60000
G1 X201.584 Y131.584 Z2.2
G1 Z1.8
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y131.584 E.42342
G1 X188.416 Y110.416 E.68067
G1 X201.584 Y110.416 E.42342
G1 X201.584 Y131.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y131.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y131.991 E.4496
G1 X188.009 Y110.009 E.70685
G1 X201.991 Y110.009 E.4496
G1 X201.991 Y131.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y132.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y132.398 E.47578
G1 X187.602 Y109.602 E.73303
G1 X202.398 Y109.602 E.47578
G1 X202.398 Y132.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y132.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y132.79 E.46408
G1 X187.21 Y109.21 E.70237
G1 X202.79 Y109.21 E.46408
G1 X202.79 Y132.73 E.70058
; WIPE_START
M204 S8000
G1 X201.79 Y132.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I1.202 J-.193 P1  F60000
G1 X201.134 Y128.648 Z2.2
G1 Z1.8
G1 E.4 F1800
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.53526
G1 F10968.03
M204 S8000
G1 X201.134 Y128.402 E.00957
G1 X200.642 Y128.402 E.01915
G1 X200.642 Y130.303 E.07394
; LINE_WIDTH: 0.51149
G1 F11524.426
G1 X200.589 Y130.373 E.00325
; LINE_WIDTH: 0.482418
G1 F12000
G1 X200.536 Y130.443 E.00305
G1 X200.303 Y130.642 E.01063
; LINE_WIDTH: 0.53532
G1 F10966.704
G1 X189.697 Y130.642 E.41252
G1 X189.36 Y130.346 E.01745
G1 X189.358 Y128.402 E.07562
G1 X188.866 Y128.402 E.01915
G1 X188.866 Y130.303 E.07395
; LINE_WIDTH: 0.516049
G1 F11413.395
G1 X188.847 Y130.599 E.0111
; LINE_WIDTH: 0.477625
G1 F12000
G1 X188.827 Y130.895 E.0102
; LINE_WIDTH: 0.427323
G1 X188.808 Y131.192 E.00902
G1 X189.289 Y131.192 E.0146
; LINE_WIDTH: 0.439202
G1 X189.425 Y131.173 E.0043
; LINE_WIDTH: 0.477625
G1 X189.561 Y131.153 E.00472
; LINE_WIDTH: 0.535015
G1 F10973.503
G1 X189.697 Y131.134 E.00534
G1 X200.303 Y131.134 E.41227
; LINE_WIDTH: 0.516049
G1 F11413.395
G1 X200.599 Y131.153 E.0111
; LINE_WIDTH: 0.477625
G1 F12000
G1 X200.895 Y131.173 E.0102
; LINE_WIDTH: 0.433565
G1 X201.192 Y131.192 E.00916
G1 X201.182 Y130.711 E.01485
; LINE_WIDTH: 0.46395
G1 X201.158 Y130.507 E.00683
; LINE_WIDTH: 0.53255
G1 F11028.751
G1 X201.134 Y130.303 E.00794
G1 X201.134 Y128.708 E.06169
; WIPE_START
G1 X201.134 Y129.708 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-1.158 J-.374 P1  F60000
G1 X200.805 Y130.727 Z2.2
G1 Z1.8
G1 E.4 F1800
; LINE_WIDTH: 0.49672
G1 F11899.515
M204 S8000
G2 X200.801 Y130.825 I-.028 J.048 E.0083
; WIPE_START
G1 X200.748 Y130.825 E-.09081
G1 X200.72 Y130.776 E-.0964
G1 X200.748 Y130.727 E-.0964
G1 X200.805 Y130.727 E-.0964
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I0 J-1.217 P1  F60000
G1 X189.252 Y130.727 Z2.2
G1 Z1.8
G1 E.4 F1800
; LINE_WIDTH: 0.4967
G1 F11900.039
M204 S8000
G2 X189.249 Y130.825 I-.028 J.048 E.0083
; WIPE_START
G1 X189.195 Y130.825 E-.09082
G1 X189.167 Y130.776 E-.09639
G1 X189.195 Y130.727 E-.09639
G1 X189.252 Y130.727 E-.09639
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I1.211 J.116 P1  F60000
G1 X189.518 Y127.952 Z2.2
G1 Z1.8
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.764 Y127.198 E.03429
G1 X188.764 Y126.603 E.01913
G1 X201.236 Y123.261 E.41517
G1 X201.236 Y122.224 E.03337
G1 X197.121 Y118.109 E.18713
G2 X197.389 Y117.907 I-.876 J-1.443 E.01082
G1 X201.236 Y116.876 E.12806
M204 S10000
G1 X201.236 Y116.99 F60000
G1 F13265.217
M204 S8000
G1 X198.726 Y114.481 E.11411
G2 X198.553 Y113.763 I-3.792 J.534 E.02377
G1 X201.236 Y113.045 E.08929
G1 X201.236 Y113.501 E.01468
G1 X198.499 Y110.764 E.12445
G1 X198.836 Y110.764 E.01086
G1 X198.222 Y113.058 E.07635
G2 X197.94 Y112.651 I-2.177 J1.207 E.01595
G1 X201.236 Y111.768 E.10971
M204 S10000
G1 X201.236 Y111.757 F60000
G1 F13265.217
M204 S8000
G1 X200.243 Y110.764 E.04512
G1 X196.781 Y111.684 E.1152
G3 X197.235 Y111.974 I-1.22 J2.416 E.01736
G1 X197.559 Y110.764 E.04026
G1 X198.295 Y110.764 E.02366
; WIPE_START
G1 X197.559 Y110.764 E-.27965
G1 X197.491 Y111.02 E-.10035
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I.216 J-1.198 P1  F60000
G1 X196.079 Y110.764 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X195.447 Y110.764 E.0203
G1 X188.764 Y112.555 E.22248
G1 X188.764 Y113.242 E.02208
G1 X191.321 Y115.799 E.11628
M204 S10000
G1 X191.302 Y115.706 F60000
G1 F13265.217
M204 S8000
G1 X188.764 Y116.386 E.08448
G1 X188.764 Y116.731 E.01108
G1 X200.209 Y128.176 E.52047
G1 X200.192 Y128.649 E.01524
G1 X194.435 Y130.192 E.19166
G1 X193.834 Y130.192 E.01931
; WIPE_START
G1 X194.435 Y130.192 E-.22814
G1 X194.821 Y130.089 E-.15186
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-.039 J-1.216 P1  F60000
G1 X191.555 Y130.192 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X191.077 Y130.192 E.01538
G1 X194.165 Y118.668 E.38364
G1 X201.236 Y125.713 E.32097
G1 X201.236 Y125.642 E.00229
G1 X200.617 Y127.952 E.07691
G1 X201.236 Y127.952 E.01991
G1 X201.236 Y127.661 E.00936
; WIPE_START
G1 X201.236 Y127.952 E-.11058
G1 X200.617 Y127.952 E-.23523
G1 X200.64 Y127.865 E-.03418
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-1.108 J-.502 P1  F60000
G1 X200.192 Y128.853 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G3 X200.016 Y130.192 I-2.587 J.342 E.04393
G1 X199.201 Y130.192 E.02622
G1 X200.192 Y129.903 E.0332
G1 X188.764 Y118.475 E.51968
G1 X188.764 Y117.663 E.02611
G1 X191.735 Y116.868 E.09888
G2 X191.989 Y117.255 I2.068 J-1.079 E.01493
G1 X189.123 Y127.952 E.3561
G1 X188.764 Y127.952 E.01152
G1 X188.764 Y127.88 E.00231
G1 X201.236 Y124.539 E.41517
G1 X201.236 Y123.968 E.01833
G1 X195.917 Y118.65 E.24186
G3 X195.422 Y118.741 I-1.155 J-4.898 E.01619
G1 X192.354 Y130.192 E.38122
G1 X191.758 Y130.192 E.01914
G1 X189.808 Y128.242 E.0887
G1 X189.808 Y128.878 E.02045
G1 X201.236 Y125.816 E.38043
G1 X201.236 Y126.038 E.00716
; WIPE_START
G1 X201.236 Y125.816 E-.08457
G1 X200.485 Y126.017 E-.29543
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I1.196 J.223 P1  F60000
G1 X201.236 Y121.984 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X188.764 Y125.326 E.41517
G1 X188.764 Y125.454 E.0041
G1 X193.503 Y130.192 E.21549
G1 X193.631 Y130.192 E.00411
G1 X196.819 Y118.295 E.39606
G3 X196.113 Y118.595 I-1.947 J-3.602 E.02468
M204 S10000
G1 X195.219 Y118.756 F60000
G1 F13265.217
M204 S8000
G3 X194.378 Y118.713 I-.217 J-4.033 E.02713
G1 X188.764 Y120.22 E.1869
G1 X198.739 Y130.192 E.45355
G1 X201.236 Y120.876 E.31015
G1 X201.236 Y120.707 E.00541
G1 X188.764 Y124.049 E.41517
M204 S10000
G1 X188.764 Y123.709 F60000
G1 F13265.217
M204 S8000
G1 X195.248 Y130.192 E.29482
M204 S10000
G1 X194.908 Y130.192 F60000
G1 F13265.217
M204 S8000
G1 X200.114 Y110.764 E.64676
G1 X199.817 Y110.764 E.00954
M204 S10000
G1 X200.447 Y110.764 F60000
G1 F13265.217
M204 S8000
G1 X201.236 Y110.764 E.02536
G1 X201.236 Y111.343 E.01861
G1 X196.185 Y130.192 E.62749
G1 X196.789 Y130.192 E.01941
; WIPE_START
G1 X196.185 Y130.192 E-.22933
G1 X196.288 Y129.809 E-.15067
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I1.21 J.126 P1  F60000
G1 X197.542 Y117.773 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G2 X198.011 Y117.255 I-1.828 J-2.128 E.02254
G1 X201.236 Y120.479 E.14663
G1 X201.236 Y119.43 E.03374
G1 X188.764 Y122.772 E.41517
G1 X188.764 Y122.168 E.01942
; WIPE_START
G1 X188.764 Y122.772 E-.22945
G1 X189.147 Y122.669 E-.15056
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-1.202 J-.188 P1  F60000
G1 X188.764 Y125.122 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X188.764 Y124.523 E.01928
G1 X191.246 Y115.26 E.30836
G3 X191.251 Y114.636 I3.116 J-.286 E.0201
M204 S10000
G1 X191.402 Y113.887 F60000
G1 F13265.217
M204 S8000
G3 X191.802 Y113.018 I3.826 J1.237 E.03083
G1 X188.764 Y113.832 E.10113
; WIPE_START
G1 X189.73 Y113.573 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-1.141 J-.422 P1  F60000
G1 X188.764 Y116.183 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X188.764 Y115.109 E.03452
G1 X191.281 Y114.435 E.08377
G3 X191.351 Y114.084 I1.791 J.177 E.01153
G1 X188.764 Y111.497 E.11763
G1 X188.764 Y111.278 E.00705
G1 X190.681 Y110.764 E.06381
G1 X190.97 Y110.764 E.0093
M204 S10000
G1 X191.724 Y110.764 F60000
G1 F13265.217
M204 S8000
G1 X192.451 Y110.764 E.02337
G1 X191.882 Y112.887 E.07068
G1 X189.776 Y110.764 E.09616
M204 S10000
G1 X189.897 Y110.764 F60000
G1 F13265.217
M204 S8000
G1 X188.764 Y114.991 E.14069
G1 X201.236 Y127.457 E.56704
G1 X201.236 Y127.093 E.01173
G1 X189.808 Y130.161 E.38048
G1 X193.014 Y118.197 E.39828
G3 X192.612 Y117.91 I2.791 J-4.329 E.0159
G1 X188.764 Y118.941 E.12807
; WIPE_START
G1 X189.73 Y118.682 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-.985 J-.714 P1  F60000
G1 X188.764 Y120.014 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X188.764 Y119.757 E.00828
G1 X191.174 Y110.764 E.29936
G1 X191.521 Y110.764 E.01115
G1 X192.744 Y111.988 E.05562
G3 X193.165 Y111.713 I2.938 J4.051 E.01617
M204 S10000
G1 X193.52 Y111.539 F60000
G1 F13265.217
M204 S8000
G1 X193.728 Y110.764 E.0258
G1 X193.265 Y110.764 E.01488
G1 X193.902 Y111.401 E.02895
M204 S10000
G1 X194.879 Y111.237 F60000
G1 F13265.217
M204 S8000
G1 X195.005 Y110.764 E.01572
M204 S10000
G1 X195.01 Y110.764 F60000
G1 F13265.217
M204 S8000
G1 X195.519 Y111.274 E.02316
G3 X196.111 Y111.405 I-.571 J3.982 E.01951
G1 X196.282 Y110.764 E.02131
G1 X196.754 Y110.764 E.01518
G1 X201.236 Y115.246 E.20379
G1 X201.236 Y115.599 E.01136
G1 X198.521 Y116.326 E.09038
M204 S10000
G1 X198.602 Y116.101 F60000
G1 F13265.217
M204 S8000
G1 X201.236 Y118.735 E.11978
G1 X201.236 Y118.153 E.0187
G1 X188.764 Y121.495 E.41517
G1 X188.764 Y121.964 E.0151
M73 P53 R7
G1 X196.992 Y130.192 E.37416
G1 X197.462 Y130.192 E.01512
G1 X201.236 Y116.109 E.46882
G1 X201.236 Y115.802 E.00987
M204 S10000
G1 X201.236 Y115.042 F60000
G1 F13265.217
M204 S8000
G1 X201.236 Y114.322 E.02316
G1 X198.766 Y114.984 E.08222
; OBJECT_ID: 8
; COOLING_NODE: 0
; WIPE_START
G1 X199.732 Y114.725 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 12
M625
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z2.2 I-.02 J-1.217 P1  F60000
G1 X141.408 Y115.684 Z2.2
G1 Z1.8
G1 E.4 F1800
; FEATURE: Inner wall
G1 F13265.217
M204 S8000
G1 X141.408 Y174.884 E1.90366
G1 X140.592 Y174.884 E.02626
G1 X140.592 Y115.684 E1.90366
G1 X120.844 Y115.684 E.63502
G1 X120.844 Y113.516 E.0697
G1 X157.584 Y113.516 E1.18143
G1 X157.584 Y115.684 E.0697
G1 X155.408 Y115.684 E.06995
G1 X155.408 Y174.884 E1.90366
G1 X154.592 Y174.884 E.02626
G1 X154.592 Y115.684 E1.90366
G1 X141.468 Y115.684 E.422
; COOLING_NODE: 0
M204 S10000
G1 X141.815 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X141.815 Y175.291 E1.90366
G1 X140.185 Y175.291 E.05244
G1 X140.185 Y116.091 E1.90366
G1 X120.437 Y116.091 E.63502
G1 X120.437 Y113.109 E.09588
G1 X157.991 Y113.109 E1.20761
G1 X157.991 Y116.091 E.09588
G1 X155.815 Y116.091 E.06995
G1 X155.815 Y175.291 E1.90366
G1 X154.185 Y175.291 E.05244
G1 X154.185 Y116.091 E1.90366
G1 X141.875 Y116.091 E.39582
; COOLING_NODE: 0
M204 S10000
G1 X142.223 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X142.223 Y174.902 E1.87806
G1 X142.937 Y174.902 E.02298
G1 X142.937 Y175.698 E.02559
G1 X139.063 Y175.698 E.12458
G1 X139.063 Y174.902 E.02559
G1 X139.777 Y174.902 E.02298
G1 X139.777 Y116.498 E1.87806
G1 X120.029 Y116.498 E.63502
G1 X120.029 Y112.702 E.12206
G1 X158.398 Y112.702 E1.23379
G1 X158.398 Y116.498 E.12206
G1 X156.223 Y116.498 E.06995
G1 X156.223 Y174.902 E1.87806
G1 X156.937 Y174.902 E.02298
G1 X156.937 Y175.698 E.02559
G1 X153.063 Y175.698 E.12458
G1 X153.063 Y174.902 E.02559
G1 X153.777 Y174.902 E.02298
G1 X153.777 Y116.498 E1.87806
G1 X142.283 Y116.498 E.36964
; COOLING_NODE: 0
M204 S250
G1 X142.615 Y116.89 F60000
M106 S127.5
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F3199
M204 S5000
G1 X142.615 Y174.51 E1.7163
G1 X143.329 Y174.51 E.02128
G1 X143.329 Y176.09 E.04706
G1 X138.671 Y176.09 E.13876
G1 X138.671 Y174.51 E.04706
G1 X139.385 Y174.51 E.02128
G1 X139.385 Y116.89 E1.7163
G1 X123.769 Y116.89 E.46517
G1 X123.369 Y116.89 E.01191
G1 X122.969 Y116.89 E.01191
G1 X122.569 Y116.89 E.01191
G1 X122.169 Y116.89 E.01191
G1 X121.769 Y116.89 E.01191
G1 X121.369 Y116.89 E.01191
G1 X120.969 Y116.89 E.01191
G1 X120.569 Y116.89 E.01191
G1 X120.169 Y116.89 E.01191
G1 X119.769 Y116.89 E.01191
G1 F2728.423
G1 X119.637 Y116.89 E.00391
M106 S61.2
M106 S127.5
G1 F2520
G1 X119.637 Y112.31 E.13642
M106 S61.2
M106 S127.5
G1 F2728.423
G1 X119.769 Y112.31 E.00391
M106 S61.2
G1 F3199
G1 X120.169 Y112.31 E.01191
G1 X120.569 Y112.31 E.01191
G1 X120.969 Y112.31 E.01191
G1 X121.369 Y112.31 E.01191
G1 X121.769 Y112.31 E.01191
G1 X122.169 Y112.31 E.01191
G1 X122.569 Y112.31 E.01191
G1 X122.969 Y112.31 E.01191
G1 X123.369 Y112.31 E.01191
G1 X123.769 Y112.31 E.01191
G1 X158.79 Y112.31 E1.04316
G1 X158.79 Y116.89 E.13642
G1 X156.615 Y116.89 E.0648
M73 P54 R7
G1 X156.615 Y174.51 E1.7163
G1 X157.329 Y174.51 E.02128
G1 X157.329 Y176.09 E.04706
G1 X152.671 Y176.09 E.13876
G1 X152.671 Y174.51 E.04706
G1 X153.385 Y174.51 E.02128
G1 X153.385 Y116.89 E1.7163
G1 X142.675 Y116.89 E.31904
; WIPE_START
G1 F12000
M204 S8000
G1 X142.674 Y117.89 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I1 J-.694 P1  F60000
G1 X141 Y115.48 Z2.2
G1 Z1.8
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.4526
G1 F13181.019
M204 S8000
G1 X141 Y174.68 E1.91581
; WIPE_START
G1 X141 Y173.68 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-.087 J1.214 P1  F60000
M106 S127.5
G1 X155 Y174.68 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13181.019
M204 S8000
G1 X155 Y115.48 E1.91581
; WIPE_START
G1 X155 Y116.48 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I1.209 J-.141 P1  F60000
G1 X154.744 Y114.292 Z2.2
G1 Z1.8
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X154.859 Y113.864 E.01424
M204 S10000
G1 X154.745 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X155.173 Y114.292 E.01945
G1 X156.021 Y114.292 E.02729
G1 X156.136 Y113.864 E.01424
G1 X156.489 Y113.864 E.01138
G1 X156.917 Y114.292 E.01945
G1 X157.236 Y114.292 E.01024
G1 X157.236 Y113.864 E.01375
G1 X156.693 Y113.864 E.01745
M204 S10000
G1 X155.932 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X155.624 Y113.864 E.00992
G1 X154.028 Y114.292 E.05313
G1 X153.67 Y114.292 E.01149
M204 S10000
G1 X154.486 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X153.581 Y113.864 E.02908
G1 X153.428 Y114.292 E.01461
G1 X153 Y113.864 E.01945
G1 X152.304 Y113.864 E.02238
G1 X152.19 Y114.292 E.01424
G1 X151.683 Y114.292 E.01628
G1 X151.256 Y113.864 E.01945
G1 X152.101 Y113.864 E.02717
M204 S10000
G1 X151.493 Y114.324 F60000
G1 F13265.217
M204 S8000
G1 X151.284 Y114.533 E.00953
G1 X151.284 Y115.027 E.01589
G1 X150.134 Y115.336 E.03829
G1 X149.56 Y115.336 E.01846
; WIPE_START
G1 X150.134 Y115.336 E-.21809
G1 X150.545 Y115.225 E-.16191
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I1.051 J-.614 P1  F60000
G1 X149.75 Y113.864 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X149.356 Y115.336 E.04897
G1 X149.238 Y115.336 E.0038
G1 X147.767 Y113.864 E.0669
G1 X147.196 Y113.864 E.01835
G1 X146.802 Y115.336 E.04897
G1 X147.29 Y115.336 E.01569
; WIPE_START
G1 X146.802 Y115.336 E-.18541
G1 X146.934 Y114.841 E-.19459
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-.462 J-1.126 P1  F60000
G1 X145.728 Y115.336 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X144.278 Y113.864 E.06643
G1 X144.642 Y113.864 E.01171
G1 X144.516 Y114.333 E.0156
M204 S10000
G1 X144.48 Y114.296 F60000
G1 F13265.217
M204 S8000
G1 X146.091 Y113.864 E.05365
G1 X146.022 Y113.864 E.00222
G1 X147.493 Y115.336 E.0669
G1 X148.079 Y115.336 E.01883
G1 X148.473 Y113.864 E.04897
G1 X149.511 Y113.864 E.03338
G1 X150.982 Y115.336 E.0669
G1 X150.633 Y115.336 E.01123
G1 X151.027 Y113.864 E.04897
G1 X150.857 Y113.864 E.00546
G1 X145.367 Y115.336 E.18277
G1 X145.525 Y115.336 E.00506
G1 X145.919 Y113.864 E.04897
G1 X145.695 Y113.864 E.00721
; WIPE_START
G1 X145.919 Y113.864 E-.08516
G1 X145.718 Y114.614 E-.29485
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I.505 J-1.107 P1  F60000
G1 X144.074 Y113.864 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X143.365 Y113.864 E.02281
G1 X143.25 Y114.292 E.01424
G1 X142.961 Y114.292 E.00931
G1 X142.533 Y113.864 E.01945
G1 X142.088 Y113.864 E.01433
G1 X141.973 Y114.292 E.01424
G1 X141.216 Y114.292 E.02434
G1 X140.789 Y113.864 E.01945
M204 S10000
G1 X140.811 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X140.696 Y114.292 E.01424
M204 S10000
G1 X140.126 Y114.292 F60000
G1 F13265.217
M204 S8000
G1 X139.729 Y114.292 E.01275
G1 X141.325 Y113.864 E.05313
G1 X141.884 Y113.864 E.01798
; WIPE_START
G1 X141.325 Y113.864 E-.21242
G1 X140.899 Y113.979 E-.16759
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I.193 J-1.202 P1  F60000
G1 X140.187 Y113.864 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X139.534 Y113.864 E.02102
G1 X139.419 Y114.292 E.01424
G1 X139.472 Y114.292 E.0017
G1 X139.044 Y113.864 E.01945
G1 X138.256 Y113.864 E.02533
G1 X138.142 Y114.292 E.01424
G1 X137.727 Y114.292 E.01333
G1 X137.3 Y113.864 E.01945
G1 X136.979 Y113.864 E.0103
G1 X136.585 Y115.336 E.04897
; WIPE_START
G1 X136.844 Y114.37 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-.714 J-.985 P1  F60000
G1 X135.512 Y115.336 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X135.835 Y115.336 E.0104
G1 X137.284 Y114.947 E.04822
G1 X137.284 Y115.336 E.01248
G1 X137.026 Y115.336 E.00828
G1 X135.555 Y113.864 E.0669
M204 S10000
G1 X135.702 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X135.308 Y115.336 E.04897
G1 X133.811 Y113.864 E.0675
G1 X134.425 Y113.864 E.01976
G1 X134.031 Y115.336 E.04897
G1 X133.537 Y115.336 E.01588
G1 X132.066 Y113.864 E.0669
G1 X133.148 Y113.864 E.0348
G1 X132.754 Y115.336 E.04897
G1 X133.334 Y115.336 E.01864
; WIPE_START
G1 X132.754 Y115.336 E-.22026
G1 X132.863 Y114.929 E-.15974
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-.432 J-1.138 P1  F60000
G1 X131.793 Y115.336 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X130.321 Y113.864 E.0669
G1 X129.317 Y113.864 E.03231
G1 X128.923 Y115.336 E.04897
G1 X128.304 Y115.336 E.01991
G1 X126.832 Y113.864 E.0669
G1 X126.763 Y113.864 E.00224
G1 X126.369 Y115.336 E.04897
G1 X126.303 Y115.336 E.00211
G1 X131.871 Y113.864 E.1852
G1 X131.477 Y115.336 E.04897
; WIPE_START
G1 X131.736 Y114.37 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-.714 J-.985 P1  F60000
G1 X130.403 Y115.336 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X131.069 Y115.336 E.0214
G1 X136.559 Y113.864 E.18277
G1 X136.776 Y113.864 E.00697
; WIPE_START
G1 X136.559 Y113.864 E-.08238
G1 X135.803 Y114.067 E-.29762
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I.047 J-1.216 P1  F60000
G1 X130.594 Y113.864 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X130.2 Y115.336 E.04897
G1 X130.048 Y115.336 E.00488
G1 X128.577 Y113.864 E.0669
G1 X128.04 Y113.864 E.01727
G1 X127.646 Y115.336 E.04897
G1 X128.1 Y115.336 E.01461
; WIPE_START
G1 X127.646 Y115.336 E-.17267
G1 X127.787 Y114.809 E-.20733
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I1.215 J.064 P1  F60000
G1 X127.836 Y113.864 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X127.027 Y113.864 E.02603
G1 X121.537 Y115.336 E.18277
G1 X121.26 Y115.336 E.00889
G1 X121.654 Y113.864 E.04897
G1 X121.599 Y113.864 E.00179
G1 X123.07 Y115.336 E.0669
G1 X123.814 Y115.336 E.02394
G1 X124.209 Y113.864 E.04897
G1 X124.884 Y113.864 E.02173
; WIPE_START
G1 X124.209 Y113.864 E-.25682
G1 X124.125 Y114.178 E-.12318
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I.266 J-1.187 P1  F60000
G1 X122.728 Y113.864 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X122.261 Y113.864 E.01503
G1 X121.192 Y114.151 E.03558
G1 X121.192 Y113.864 E.00921
G1 X121.395 Y113.864 E.00654
; WIPE_START
G1 X121.192 Y113.864 E-.0773
G1 X121.192 Y114.151 E-.10882
G1 X121.685 Y114.019 E-.19389
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-1.022 J.661 P1  F60000
G1 X122.537 Y115.336 Z2.2
G1 Z1.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X122.931 Y113.864 E.04897
G1 X123.343 Y113.864 E.01325
G1 X124.814 Y115.336 E.0669
G1 X125.091 Y115.336 E.00891
G1 X125.486 Y113.864 E.04897
G1 X125.088 Y113.864 E.01279
G1 X126.559 Y115.336 E.0669
; WIPE_START
G1 X125.852 Y114.628 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-.007 J1.217 P1  F60000
G1 X144.267 Y114.742 Z2.2
G1 Z1.8
G1 E.4 F1800
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.53531
G1 F10966.917
M204 S8000
G1 X141.829 Y114.742 E.09483
; LINE_WIDTH: 0.518357
G1 F11357.98
G1 X141.696 Y114.725 E.00503
; LINE_WIDTH: 0.48445
G1 F12000
G1 X141.563 Y114.708 E.00467
; LINE_WIDTH: 0.435876
G1 X141.43 Y114.691 E.00416
G1 X140.57 Y114.691 E.02669
; LINE_WIDTH: 0.450542
G1 X140.437 Y114.708 E.00431
; LINE_WIDTH: 0.484445
G1 X140.304 Y114.725 E.00467
; LINE_WIDTH: 0.534907
G1 F10975.904
G1 X140.171 Y114.742 E.00521
G1 X137.733 Y114.742 E.09476
G1 X137.733 Y115.234 E.01914
G1 X140.338 Y115.234 E.10122
G1 X140.371 Y115.132 E.00416
; LINE_WIDTH: 0.518349
G1 F11358.179
G1 X140.437 Y115.115 E.00258
; LINE_WIDTH: 0.484445
G1 F12000
G1 X140.504 Y115.098 E.00239
; LINE_WIDTH: 0.434842
G1 X140.57 Y115.081 E.00212
G1 X141.43 Y115.081 E.02662
; LINE_WIDTH: 0.450544
G1 X141.496 Y115.098 E.00221
; LINE_WIDTH: 0.48445
G1 X141.563 Y115.115 E.00239
; LINE_WIDTH: 0.534948
G1 F10974.983
G1 X141.629 Y115.132 E.00267
G1 X141.662 Y115.234 E.00416
G1 X144.267 Y115.234 E.10123
G1 X144.267 Y114.802 E.01681
; WIPE_START
G1 X144.267 Y115.234 E-.16431
G1 X143.699 Y115.234 E-.21569
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I.022 J1.217 P1  F60000
G1 X157.134 Y114.988 Z2.2
G1 Z1.8
G1 E.4 F1800
; LINE_WIDTH: 0.535305
G1 F10967.046
M204 S8000
G1 X157.134 Y114.742 E.00958
G1 X155.829 Y114.742 E.05078
; LINE_WIDTH: 0.518357
G1 F11357.98
G1 X155.696 Y114.725 E.00503
; LINE_WIDTH: 0.48445
G1 F12000
G1 X155.563 Y114.708 E.00467
; LINE_WIDTH: 0.435876
G1 X155.43 Y114.691 E.00416
G1 X154.57 Y114.691 E.02669
; LINE_WIDTH: 0.450542
G1 X154.437 Y114.708 E.00431
; LINE_WIDTH: 0.484445
G1 X154.304 Y114.725 E.00467
; LINE_WIDTH: 0.534907
G1 F10975.904
G1 X154.171 Y114.742 E.00521
G1 X151.733 Y114.742 E.09476
G1 X151.733 Y115.234 E.01914
G1 X154.338 Y115.234 E.10122
G1 X154.371 Y115.132 E.00416
; LINE_WIDTH: 0.518349
G1 F11358.179
G1 X154.437 Y115.115 E.00258
; LINE_WIDTH: 0.484445
G1 F12000
G1 X154.504 Y115.098 E.00239
; LINE_WIDTH: 0.434842
G1 X154.57 Y115.081 E.00212
G1 X155.43 Y115.081 E.02662
; LINE_WIDTH: 0.450544
G1 X155.496 Y115.098 E.00221
; LINE_WIDTH: 0.48445
G1 X155.563 Y115.115 E.00239
; LINE_WIDTH: 0.534671
G1 F10981.171
G1 X155.629 Y115.132 E.00266
G1 X155.662 Y115.234 E.00415
G1 X157.134 Y115.234 E.05717
G1 X157.134 Y115.048 E.00723
; COOLING_NODE: 0
; WIPE_START
G1 X157.134 Y115.234 E-.07075
G1 X156.32 Y115.234 E-.30925
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I-.013 J-1.217 P1  F60000
G1 X115.156 Y115.684 Z2.2
G1 Z1.8
M73 P55 R7
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
M73 P55 R6
G1 X112.416 Y115.684 E.08811
G1 X112.416 Y113.516 E.0697
G1 X115.156 Y113.516 E.08811
G1 X115.156 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X115.563 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X112.009 Y116.091 E.11429
G1 X112.009 Y113.109 E.09588
G1 X115.563 Y113.109 E.11429
G1 X115.563 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X115.97 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X111.602 Y116.498 E.14047
G1 X111.602 Y112.702 E.12206
G1 X115.97 Y112.702 E.14047
G1 X115.97 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X116.231 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F3199
M204 S5000
G1 X111.21 Y116.89 E.14957
G1 X111.21 Y112.31 E.13642
G1 X112.231 Y112.31 E.03042
G1 X112.631 Y112.31 E.01191
G1 X113.031 Y112.31 E.01191
G1 X113.431 Y112.31 E.01191
G1 X113.831 Y112.31 E.01191
G1 X114.231 Y112.31 E.01191
G1 X114.631 Y112.31 E.01191
G1 X115.031 Y112.31 E.01191
G1 X115.431 Y112.31 E.01191
G1 X115.831 Y112.31 E.01191
G1 X116.231 Y112.31 E.01191
G1 F2728.407
G1 X116.363 Y112.31 E.00391
M106 S61.2
M106 S127.5
G1 F2520
G1 X116.363 Y116.89 E.13642
M106 S61.2
M106 S127.5
G1 F2632.166
G1 X116.291 Y116.89 E.00212
M106 S61.2
; WIPE_START
M204 S8000
G1 X115.291 Y116.89 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.2 I1.156 J-.381 P1  F60000
G1 X114.764 Y115.292 Z2.2
G1 Z1.8
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X114.764 Y113.908 E.04121
G1 X112.808 Y113.908 E.05826
G1 X112.808 Y115.292 E.04121
G1 X114.704 Y115.292 E.05648
M204 S10000
G1 X114.324 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X114.324 Y114.348 E.02
G1 X113.248 Y114.348 E.04276
G1 X113.248 Y114.852 E.02
G1 X114.264 Y114.852 E.04038
; CHANGE_LAYER
; Z_HEIGHT: 2
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F10731.32
G1 X113.264 Y114.852 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 10/27
; update layer progress
M73 L10
M991 S0 P9 ;notify layer change
; OBJECT_ID: 16
; COOLING_NODE: 0
; start printing object, unique label id: 16
M624 BAAAAAAAAAA=
M204 S10000
G17
G3 Z2.2 I-.746 J.962 P1  F60000
G1 X195.198 Y178.408 Z2.2
G1 Z2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X195.085 Y178.414 E.00364
G3 X194.575 Y171.609 I-.085 J-3.416 E.3342
G1 X194.915 Y171.583 E.01096
G3 X195.425 Y178.389 I.085 J3.416 E.33418
G1 X195.258 Y178.403 E.00538
; COOLING_NODE: 0
M204 S10000
G1 X195.168 Y178.003 F60000
G1 F13265.217
M204 S8000
G1 X195.075 Y178.007 E.00299
G3 X194.626 Y172.013 I-.075 J-3.008 E.29436
G1 X194.925 Y171.991 E.00965
G3 X195.374 Y177.985 I.075 J3.008 E.29435
G1 X195.228 Y177.997 E.00473
; COOLING_NODE: 0
M204 S10000
G1 X195.137 Y177.597 F60000
G1 F13265.217
M204 S8000
G1 X195.065 Y177.601 E.00233
G3 X194.676 Y172.417 I-.065 J-2.601 E.25453
G1 X194.935 Y172.398 E.00835
G3 X195.324 Y177.581 I.065 J2.601 E.25452
G1 X195.197 Y177.592 E.00408
; COOLING_NODE: 0
M204 S250
G1 X195.107 Y177.203 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X195.055 Y177.199 E.00157
G3 X194.725 Y172.807 I-.055 J-2.204 E.19976
G1 X194.945 Y172.79 E.00657
G3 X195.489 Y177.144 I.055 J2.204 E.19323
G1 X195.167 Y177.194 E.00972
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X195.055 Y177.199 E-.04254
G1 X194.616 Y177.177 E-.16685
G1 X194.192 Y177.057 E-.1673
G1 X194.185 Y177.054 E-.00331
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I-1.084 J.552 P1  F60000
G1 X201.584 Y191.584 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y191.584 E.42342
G1 X188.416 Y170.416 E.68067
G1 X201.584 Y170.416 E.42342
G1 X201.584 Y191.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y191.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y191.991 E.4496
G1 X188.009 Y170.009 E.70685
G1 X201.991 Y170.009 E.4496
G1 X201.991 Y191.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y192.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y192.398 E.47578
G1 X187.602 Y169.602 E.73303
G1 X202.398 Y169.602 E.47578
G1 X202.398 Y192.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y192.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y192.79 E.46408
G1 X187.21 Y169.21 E.70237
G1 X202.79 Y169.21 E.46408
G1 X202.79 Y192.73 E.70058
; object ids of layer 10 start: 8,12,16
M624 BwAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer10 end: 8,12,16
M625
; WIPE_START
M204 S8000
G1 X201.79 Y192.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I.591 J-1.064 P1  F60000
G1 X198.414 Y190.858 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X200.858 Y181.647 E.30646
G1 X197.507 Y178.295 E.15242
G3 X196.713 Y178.773 I-2.755 J-3.676 E.02985
; WIPE_START
G1 X197.507 Y178.295 E-.35212
G1 X197.559 Y178.347 E-.02788
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I1.172 J.326 P1  F60000
G1 X198.697 Y174.253 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.38292
G1 F12000
M204 S8000
G1 X198.475 Y173.534 E.02019
G1 X198.116 Y172.875 E.02016
G1 X197.622 Y172.289 E.02061
G1 X197.061 Y171.842 E.01926
G1 X196.378 Y171.489 E.02064
G1 X195.654 Y171.285 E.02019
G1 X194.914 Y171.221 E.01997
G1 X194.176 Y171.32 E.02001
G1 X193.463 Y171.557 E.02017
G1 X192.811 Y171.93 E.02018
G1 X192.491 Y172.172 E.01077
G1 X192.111 Y172.567 E.01472
G1 X191.693 Y173.182 E.01997
G1 X191.393 Y173.871 E.02019
G1 X191.241 Y174.608 E.02021
G1 X191.238 Y175.361 E.02021
G1 X191.384 Y176.099 E.02022
G1 X191.665 Y176.777 E.01973
G1 X192.094 Y177.417 E.02067
G1 X192.631 Y177.945 E.02023
G1 X193.278 Y178.364 E.02071
G1 X193.961 Y178.634 E.01973
G1 X194.702 Y178.768 E.02021
G1 X195.454 Y178.752 E.02021
G1 X196.189 Y178.588 E.02021
G1 X196.876 Y178.281 E.02022
G1 X197.489 Y177.844 E.02021
G2 X198.608 Y176.129 I-2.782 J-3.036 E.05559
G1 X198.751 Y175.391 E.0202
G1 X198.754 Y174.639 E.02018
G1 X198.706 Y174.312 E.00888
; WIPE_START
G1 X198.754 Y174.639 E-.12568
G1 X198.751 Y175.309 E-.25432
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I-1.215 J.074 P1  F60000
G1 X198.827 Y176.56 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G3 X198.366 Y177.41 I-3.517 J-1.356 E.03119
G1 X200.858 Y179.902 E.11332
G1 X200.858 Y179.678 E.00722
G1 X189.142 Y182.817 E.39006
G1 X189.142 Y182.569 E.00798
G1 X190.944 Y175.844 E.22389
G1 X190.969 Y175.942 E.00327
G1 X189.142 Y176.432 E.06082
G1 X189.142 Y175.367 E.03424
M204 S10000
G1 X189.142 Y174.951 F60000
G1 F13265.217
M204 S8000
G1 X189.142 Y173.878 E.03452
G1 X191.22 Y173.321 E.0692
G1 X191.097 Y173.63 E.01071
G1 X189.142 Y171.674 E.08893
G1 X189.142 Y171.323 E.01129
G1 X189.82 Y171.142 E.02258
G1 X189.649 Y171.142 E.00548
G1 X189.142 Y173.037 E.06309
G1 X189.142 Y173.419 E.0123
G1 X190.863 Y175.14 E.07827
G3 X190.871 Y174.691 I2.246 J-.182 E.01446
G1 X189.142 Y175.164 E.05765
G1 X200.858 Y186.88 E.53283
G1 X200.858 Y186.503 E.01213
G1 X199.691 Y190.858 E.145
G1 X199.603 Y190.858 E.00284
G1 X189.142 Y180.397 E.47574
G1 X189.142 Y180.263 E.00431
G1 X193.887 Y178.992 E.15797
G1 X193.929 Y179.001 E.00139
G1 X190.752 Y190.858 E.39474
G1 X190.88 Y190.858 E.00413
G1 X189.142 Y189.12 E.07906
G1 X189.142 Y189.203 E.00266
G1 X200.858 Y186.063 E.39006
G1 X200.858 Y185.339 E.02328
; WIPE_START
G1 X200.858 Y186.063 E-.27506
G1 X200.592 Y186.135 E-.10494
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I-1.188 J.263 P1  F60000
G1 X200.858 Y187.34 Z2.4
G1 Z2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X189.142 Y190.48 E.39006
G1 X189.142 Y190.858 E.01218
G1 X189.475 Y190.858 E.01071
G1 X192.786 Y178.499 E.41144
M204 S10000
G1 X192.302 Y178.139 F60000
G1 F13265.217
M204 S8000
G1 X189.142 Y178.986 E.1052
G1 X189.142 Y178.653 E.01072
G1 X200.858 Y190.369 E.53283
G1 X200.858 Y189.894 E.01527
G1 X197.137 Y190.858 E.12361
G1 X200.858 Y176.971 E.46233
G1 X200.858 Y177.124 E.00492
G1 X197.94 Y177.906 E.09717
G1 X198.097 Y177.745 E.00723
G1 X194.583 Y190.858 E.43656
G1 X194.369 Y190.858 E.00687
G1 X189.142 Y185.631 E.23773
G1 X189.142 Y185.371 E.00834
G1 X200.858 Y182.232 E.39006
; WIPE_START
G1 X199.892 Y182.491 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I1.188 J.265 P1  F60000
G1 X200.858 Y178.158 Z2.4
G1 Z2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X198.95 Y176.249 E.08678
G1 X198.902 Y176.371 E.00419
G1 X200.858 Y175.846 E.06511
G1 X200.858 Y176.413 E.01822
G1 X199.128 Y174.683 E.07867
G3 X199.143 Y175.029 I-1.718 J.245 E.01115
G1 X200.858 Y174.569 E.05711
G1 X200.858 Y174.669 E.00319
G1 X197.331 Y171.142 E.16039
G1 X197.215 Y171.502 E.01216
G3 X197.438 Y171.655 I-.653 J1.186 E.00869
G1 X199.352 Y171.142 E.06374
G1 X199.076 Y171.142 E.00888
G1 X200.858 Y172.924 E.08105
M204 S10000
G1 X200.858 Y173.292 F60000
G1 F13265.217
M204 S8000
G1 X198.966 Y173.799 E.06301
G1 X199.057 Y174.16 E.01196
G1 X199.866 Y171.142 E.10048
G1 X200.858 Y171.142 E.03191
G1 X200.858 Y171.778 E.02045
; WIPE_START
G1 X200.858 Y171.142 E-.24169
G1 X200.494 Y171.142 E-.13831
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I0 J-1.217 P1  F60000
G1 X198.589 Y171.142 Z2.4
G1 Z2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X198.244 Y172.428 E.04282
M204 S10000
G1 X198.425 Y172.667 F60000
G1 F13265.217
M204 S8000
G1 X200.858 Y172.015 E.081
G1 X200.858 Y172.205 E.00609
G1 X195.86 Y190.858 E.621
G1 X196.114 Y190.858 E.00816
G1 X189.142 Y183.886 E.31707
G1 X189.142 Y184.094 E.00669
G1 X200.858 Y180.955 E.39006
G1 X200.858 Y180.106 E.0273
M204 S10000
G1 X200.858 Y179.474 F60000
G1 F13265.217
M204 S8000
G1 X200.858 Y178.401 E.03452
G1 X189.142 Y181.54 E.39006
M204 S10000
G1 X189.142 Y182.142 F60000
G1 F13265.217
M204 S8000
G1 X197.858 Y190.858 E.3964
; WIPE_START
G1 X197.151 Y190.151 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I-.132 J-1.21 P1  F60000
G1 X188.779 Y191.062 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.383193
G1 F12000
M204 S8000
G1 X188.806 Y191.194 E.00362
G1 X188.938 Y191.221 E.00362
G1 X201.062 Y191.221 E.32587
G1 X201.194 Y191.194 E.00362
G1 X201.221 Y191.062 E.00362
G1 X201.221 Y170.938 E.5409
G1 X201.194 Y170.806 E.00362
G1 X201.062 Y170.779 E.00362
G1 X188.938 Y170.779 E.32587
G1 X188.806 Y170.806 E.00362
G1 X188.779 Y170.938 E.00362
M73 P56 R6
G1 X188.779 Y191.002 E.53929
; WIPE_START
G1 X188.779 Y190.002 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I1.154 J.386 P1  F60000
G1 X189.142 Y188.916 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X189.142 Y187.926 E.03186
G1 X200.858 Y184.786 E.39006
G1 X200.858 Y185.136 E.01125
G1 X194.86 Y179.137 E.2728
G2 X195.169 Y179.138 I.16 J-1.546 E.00997
G1 X192.029 Y190.858 E.39018
G1 X191.084 Y190.858 E.03039
; WIPE_START
G1 X192.029 Y190.858 E-.35912
G1 X192.043 Y190.805 E-.02089
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I-.051 J1.216 P1  F60000
G1 X193.306 Y190.858 Z2.4
G1 Z2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X196.524 Y178.848 E.39982
G1 X196.374 Y178.907 E.00517
G1 X200.858 Y183.391 E.20392
G1 X200.858 Y183.509 E.00379
G1 X189.142 Y186.648 E.39006
; WIPE_START
G1 X190.108 Y186.39 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I1.211 J-.123 P1  F60000
G1 X189.142 Y176.908 Z2.4
G1 Z2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X200.858 Y188.625 E.53283
G1 X192.494 Y190.858 E.27838
G1 X192.625 Y190.858 E.00419
G1 X189.142 Y187.375 E.1584
G1 X191.757 Y177.574 E.3262
M204 S10000
G1 X191.432 Y177.095 F60000
G1 F13265.217
M204 S8000
G1 X189.142 Y177.709 E.07624
G1 X189.142 Y177.803 E.00302
G1 X190.926 Y171.142 E.22175
G1 X190.353 Y171.142 E.01843
G1 X191.706 Y172.494 E.0615
G3 X191.906 Y172.253 I2.424 J1.811 E.01007
G1 X192.204 Y171.142 E.03701
G1 X192.098 Y171.142 E.0034
G1 X192.587 Y171.631 E.02225
G1 X192.498 Y171.701 E.00365
G1 X189.142 Y172.6 E.11173
; WIPE_START
G1 X190.108 Y172.342 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I.563 J1.079 P1  F60000
G1 X192.407 Y171.142 Z2.4
G1 Z2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X193.481 Y171.142 E.03452
G2 X192.758 Y171.521 I6.085 J12.48 E.02624
; OBJECT_ID: 12
; COOLING_NODE: 0
; WIPE_START
G1 X193.481 Y171.142 E-.31
G1 X193.296 Y171.142 E-.07
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 16
M625
; start printing object, unique label id: 12
M624 AgAAAAAAAAA=
M204 S10000
G17
G3 Z2.4 I1.213 J.094 P1  F60000
G1 X197.449 Y117.38 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Inner wall
G1 F13265.217
M204 S8000
G1 X197.259 Y117.56 E.0084
G3 X194.575 Y111.609 I-2.259 J-2.562 E.41075
G1 X194.915 Y111.583 E.01096
G3 X197.503 Y117.322 I.085 J3.415 E.25748
G1 X197.49 Y117.336 E.00062
; COOLING_NODE: 0
M204 S10000
G1 X197.165 Y117.089 F60000
G1 F13265.217
M204 S8000
G1 X196.99 Y117.255 E.00775
G3 X194.626 Y112.013 I-1.99 J-2.257 E.36177
G1 X194.925 Y111.991 E.00965
G3 X197.205 Y117.045 I.075 J3.008 E.22674
; COOLING_NODE: 0
M204 S10000
G1 X196.88 Y116.797 F60000
G1 F13265.217
M204 S8000
G1 X196.72 Y116.949 E.0071
G3 X194.676 Y112.417 I-1.72 J-1.951 E.31279
G1 X194.935 Y112.398 E.00835
G3 X196.92 Y116.753 I.065 J2.6 E.19539
; COOLING_NODE: 0
M204 S250
G1 X196.606 Y116.516 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X196.289 Y116.793 E.01255
G3 X194.725 Y112.807 I-1.289 J-1.794 E.23948
G1 X194.945 Y112.79 E.00657
G3 X196.646 Y116.471 I.055 J2.208 E.15301
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X196.289 Y116.793 E-.18266
G1 X195.909 Y117.015 E-.1671
G1 X195.834 Y117.04 E-.03025
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I-1.132 J.447 P1  F60000
G1 X201.584 Y131.584 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y131.584 E.42342
G1 X188.416 Y110.416 E.68067
G1 X201.584 Y110.416 E.42342
G1 X201.584 Y131.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y131.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y131.991 E.4496
G1 X188.009 Y110.009 E.70685
G1 X201.991 Y110.009 E.4496
G1 X201.991 Y131.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y132.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y132.398 E.47578
G1 X187.602 Y109.602 E.73303
G1 X202.398 Y109.602 E.47578
G1 X202.398 Y132.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y132.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y132.79 E.46408
G1 X187.21 Y109.21 E.70237
G1 X202.79 Y109.21 E.46408
G1 X202.79 Y132.73 E.70058
; WIPE_START
M204 S8000
G1 X201.79 Y132.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I.591 J-1.064 P1  F60000
G1 X198.414 Y130.858 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X200.858 Y121.647 E.30646
G1 X197.507 Y118.295 E.15242
G3 X196.713 Y118.773 I-2.753 J-3.673 E.02985
; WIPE_START
G1 X197.507 Y118.295 E-.35212
G1 X197.559 Y118.347 E-.02788
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I1.172 J.326 P1  F60000
G1 X198.697 Y114.253 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.38292
G1 F12000
M204 S8000
G1 X198.475 Y113.534 E.02019
G1 X198.116 Y112.875 E.02016
G1 X197.634 Y112.3 E.02017
G1 X197.047 Y111.832 E.02016
G1 X196.378 Y111.489 E.02018
G1 X195.654 Y111.285 E.02019
G1 X194.914 Y111.221 E.01997
G1 X194.176 Y111.32 E.02001
G1 X193.463 Y111.557 E.02017
G1 X192.811 Y111.929 E.02017
G1 X192.491 Y112.172 E.01078
G1 X192.111 Y112.567 E.01473
G1 X191.693 Y113.182 E.01996
G1 X191.393 Y113.871 E.02019
G1 X191.241 Y114.608 E.02021
G1 X191.238 Y115.361 E.02021
G1 X191.384 Y116.099 E.02022
G1 X191.673 Y116.794 E.02022
G1 X192.094 Y117.417 E.02021
G1 X192.631 Y117.945 E.02022
G1 X193.261 Y118.356 E.02021
G1 X193.961 Y118.634 E.02022
G1 X194.702 Y118.768 E.02022
G1 X195.455 Y118.752 E.02022
G1 X196.189 Y118.588 E.02021
G1 X196.876 Y118.281 E.02021
G1 X197.489 Y117.844 E.02021
G2 X198.608 Y116.129 I-2.782 J-3.036 E.05558
G1 X198.751 Y115.391 E.0202
G1 X198.754 Y114.639 E.02018
G1 X198.706 Y114.312 E.00888
; WIPE_START
G1 X198.754 Y114.639 E-.12566
G1 X198.751 Y115.309 E-.25434
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I-1.215 J.074 P1  F60000
G1 X198.827 Y116.56 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G3 X198.366 Y117.41 I-3.521 J-1.358 E.03119
G1 X200.858 Y119.902 E.11332
G1 X200.858 Y119.678 E.00722
G1 X189.142 Y122.817 E.39006
G1 X189.142 Y122.569 E.00798
G1 X190.944 Y115.844 E.22389
G1 X190.969 Y115.942 E.00327
G1 X189.142 Y116.432 E.06082
G1 X189.142 Y115.367 E.03424
M204 S10000
G1 X189.142 Y114.951 F60000
G1 F13265.217
M204 S8000
G1 X189.142 Y113.878 E.03452
G1 X191.22 Y113.321 E.0692
G1 X191.097 Y113.63 E.01071
G1 X189.142 Y111.674 E.08893
G1 X189.142 Y111.323 E.01129
G1 X189.82 Y111.142 E.02258
G1 X189.649 Y111.142 E.00548
G1 X189.142 Y113.037 E.06309
G1 X189.142 Y113.419 E.0123
G1 X190.863 Y115.14 E.07827
G3 X190.871 Y114.691 I2.244 J-.182 E.01446
G1 X189.142 Y115.164 E.05765
G1 X200.858 Y126.88 E.53283
G1 X200.858 Y126.503 E.01213
G1 X199.691 Y130.858 E.145
G1 X199.603 Y130.858 E.00284
G1 X189.142 Y120.397 E.47574
G1 X189.142 Y120.263 E.00431
G1 X193.887 Y118.992 E.15797
G1 X193.929 Y119.001 E.00139
G1 X190.752 Y130.858 E.39474
G1 X190.88 Y130.858 E.00413
G1 X189.142 Y129.12 E.07906
G1 X189.142 Y129.203 E.00266
G1 X200.858 Y126.063 E.39006
G1 X200.858 Y125.339 E.02328
; WIPE_START
G1 X200.858 Y126.063 E-.27506
G1 X200.592 Y126.135 E-.10494
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I-1.188 J.263 P1  F60000
G1 X200.858 Y127.34 Z2.4
G1 Z2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X189.142 Y130.48 E.39006
G1 X189.142 Y130.858 E.01218
G1 X189.475 Y130.858 E.01071
G1 X192.786 Y118.501 E.41138
M204 S10000
G1 X192.302 Y118.139 F60000
G1 F13265.217
M204 S8000
G1 X189.142 Y118.986 E.1052
G1 X189.142 Y118.653 E.01072
G1 X200.858 Y130.369 E.53283
G1 X200.858 Y129.894 E.01527
G1 X197.137 Y130.858 E.12361
G1 X200.858 Y116.971 E.46233
G1 X200.858 Y117.123 E.00492
G1 X197.94 Y117.906 E.09717
G1 X198.097 Y117.745 E.00722
G1 X194.583 Y130.858 E.43656
G1 X194.369 Y130.858 E.00687
G1 X189.142 Y125.631 E.23773
G1 X189.142 Y125.371 E.00834
G1 X200.858 Y122.232 E.39006
; WIPE_START
G1 X199.892 Y122.491 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I1.188 J.265 P1  F60000
G1 X200.858 Y118.158 Z2.4
G1 Z2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X198.95 Y116.249 E.08678
G1 X198.902 Y116.37 E.00419
G1 X200.858 Y115.846 E.06511
G1 X200.858 Y116.413 E.01822
G1 X199.128 Y114.683 E.07867
G3 X199.143 Y115.029 I-1.718 J.245 E.01115
G1 X200.858 Y114.569 E.05711
G1 X200.858 Y114.669 E.00319
G1 X197.331 Y111.142 E.16039
G1 X197.216 Y111.5 E.01211
G3 X197.438 Y111.655 I-.663 J1.186 E.00871
G1 X199.352 Y111.142 E.06374
G1 X199.076 Y111.142 E.00888
G1 X200.858 Y112.924 E.08105
M204 S10000
G1 X200.858 Y113.292 F60000
G1 F13265.217
M204 S8000
G1 X198.966 Y113.799 E.06301
G1 X199.057 Y114.16 E.01197
G1 X199.866 Y111.142 E.10048
G1 X200.858 Y111.142 E.03191
G1 X200.858 Y111.778 E.02045
; WIPE_START
G1 X200.858 Y111.142 E-.24169
G1 X200.494 Y111.142 E-.13831
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I0 J-1.217 P1  F60000
G1 X198.589 Y111.142 Z2.4
G1 Z2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X198.244 Y112.428 E.04282
M204 S10000
G1 X198.425 Y112.667 F60000
G1 F13265.217
M204 S8000
G1 X200.858 Y112.015 E.081
G1 X200.858 Y112.204 E.00609
G1 X195.86 Y130.858 E.621
G1 X196.114 Y130.858 E.00816
G1 X189.142 Y123.886 E.31707
G1 X189.142 Y124.094 E.00669
G1 X200.858 Y120.955 E.39006
G1 X200.858 Y120.106 E.0273
M204 S10000
G1 X200.858 Y119.474 F60000
G1 F13265.217
M204 S8000
G1 X200.858 Y118.401 E.03452
G1 X189.142 Y121.54 E.39006
M204 S10000
G1 X189.142 Y122.142 F60000
G1 F13265.217
M204 S8000
G1 X197.858 Y130.858 E.3964
; WIPE_START
G1 X197.151 Y130.151 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
M73 P57 R6
G3 Z2.4 I-.132 J-1.21 P1  F60000
G1 X188.779 Y131.062 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.383193
G1 F12000
M204 S8000
G1 X188.806 Y131.194 E.00362
G1 X188.938 Y131.221 E.00362
G1 X201.062 Y131.221 E.32587
G1 X201.194 Y131.194 E.00362
G1 X201.221 Y131.062 E.00362
G1 X201.221 Y110.938 E.5409
G1 X201.194 Y110.806 E.00362
G1 X201.062 Y110.779 E.00362
G1 X188.938 Y110.779 E.32587
G1 X188.806 Y110.806 E.00362
G1 X188.779 Y110.938 E.00362
G1 X188.779 Y131.002 E.53929
; WIPE_START
G1 X188.779 Y130.002 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I1.154 J.386 P1  F60000
G1 X189.142 Y128.916 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X189.142 Y127.925 E.03186
G1 X200.858 Y124.786 E.39006
G1 X200.858 Y125.136 E.01125
G1 X194.86 Y119.137 E.2728
G2 X195.169 Y119.138 I.16 J-1.545 E.00997
G1 X192.029 Y130.858 E.39018
G1 X191.084 Y130.858 E.03039
; WIPE_START
G1 X192.029 Y130.858 E-.35912
G1 X192.043 Y130.805 E-.02089
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I-.051 J1.216 P1  F60000
G1 X193.306 Y130.858 Z2.4
G1 Z2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X196.524 Y118.848 E.39982
G1 X196.374 Y118.907 E.00517
G1 X200.858 Y123.391 E.20392
G1 X200.858 Y123.509 E.00379
G1 X189.142 Y126.648 E.39006
; WIPE_START
G1 X190.108 Y126.39 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I1.211 J-.123 P1  F60000
G1 X189.142 Y116.908 Z2.4
G1 Z2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X200.858 Y128.625 E.53283
G1 X192.494 Y130.858 E.27838
G1 X192.625 Y130.858 E.00419
G1 X189.142 Y127.375 E.1584
G1 X191.757 Y117.574 E.3262
M204 S10000
G1 X191.43 Y117.096 F60000
G1 F13265.217
M204 S8000
G1 X189.142 Y117.709 E.07618
G1 X189.142 Y117.803 E.00302
G1 X190.926 Y111.142 E.22175
G1 X190.353 Y111.142 E.01843
G1 X191.706 Y112.494 E.0615
G3 X191.906 Y112.253 I2.414 J1.802 E.01007
G1 X192.204 Y111.142 E.03701
G1 X192.098 Y111.142 E.0034
G1 X192.587 Y111.631 E.02225
G1 X192.498 Y111.701 E.00365
G1 X189.142 Y112.6 E.11173
; WIPE_START
G1 X190.108 Y112.342 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I.563 J1.079 P1  F60000
G1 X192.407 Y111.142 Z2.4
G1 Z2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X193.481 Y111.142 E.03452
G2 X192.758 Y111.521 I6.099 J12.507 E.02624
; OBJECT_ID: 8
; COOLING_NODE: 0
; WIPE_START
G1 X193.481 Y111.142 E-.31001
G1 X193.296 Y111.142 E-.07
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 12
M625
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z2.4 I-.106 J-1.212 P1  F60000
G1 X141.235 Y115.684 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Inner wall
G1 F13265.217
M204 S8000
G1 X141.235 Y174.884 E1.90366
G1 X140.765 Y174.884 E.01513
G1 X140.765 Y115.684 E1.90366
G1 X120.615 Y115.684 E.64793
G1 X120.615 Y113.516 E.0697
G1 X157.584 Y113.516 E1.18878
G1 X157.584 Y115.684 E.0697
G1 X155.235 Y115.684 E.07552
G1 X155.235 Y174.884 E1.90366
G1 X154.765 Y174.884 E.01513
G1 X154.765 Y115.684 E1.90366
G1 X141.295 Y115.684 E.43313
; COOLING_NODE: 0
M204 S10000
G1 X141.642 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X141.642 Y175.291 E1.90366
G1 X140.358 Y175.291 E.04131
G1 X140.358 Y116.091 E1.90366
G1 X120.208 Y116.091 E.64793
G1 X120.208 Y113.109 E.09588
G1 X157.991 Y113.109 E1.21496
G1 X157.991 Y116.091 E.09588
G1 X155.642 Y116.091 E.07552
G1 X155.642 Y175.291 E1.90366
G1 X154.358 Y175.291 E.04131
G1 X154.358 Y116.091 E1.90366
G1 X141.702 Y116.091 E.40695
; COOLING_NODE: 0
M204 S10000
G1 X142.049 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X142.049 Y174.902 E1.87806
G1 X142.816 Y174.902 E.02464
G1 X142.816 Y175.698 E.02559
G1 X139.184 Y175.698 E.11678
G1 X139.184 Y174.902 E.02559
G1 X139.951 Y174.902 E.02464
G1 X139.951 Y116.498 E1.87806
G1 X119.801 Y116.498 E.64793
G1 X119.801 Y112.702 E.12206
G1 X158.398 Y112.702 E1.24113
G1 X158.398 Y116.498 E.12206
G1 X156.049 Y116.498 E.07552
G1 X156.049 Y174.902 E1.87806
G1 X156.816 Y174.902 E.02464
G1 X156.816 Y175.698 E.02559
G1 X153.184 Y175.698 E.11678
G1 X153.184 Y174.902 E.02559
G1 X153.951 Y174.902 E.02464
G1 X153.951 Y116.498 E1.87806
G1 X142.109 Y116.498 E.38077
; COOLING_NODE: 0
M204 S250
G1 X142.442 Y116.89 F60000
M106 S127.5
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F3077
M204 S5000
G1 X142.442 Y174.51 E1.7163
G1 X143.208 Y174.51 E.02283
G1 X143.208 Y176.09 E.04706
G1 X138.792 Y176.09 E.13153
M73 P58 R6
G1 X138.792 Y174.51 E.04706
G1 X139.558 Y174.51 E.02283
G1 X139.558 Y116.89 E1.7163
G1 X123.996 Y116.89 E.46354
G1 X123.596 Y116.89 E.01191
G1 X123.196 Y116.89 E.01191
G1 X122.796 Y116.89 E.01191
G1 X122.396 Y116.89 E.01191
G1 X121.996 Y116.89 E.01191
G1 X121.596 Y116.89 E.01191
G1 X121.196 Y116.89 E.01191
G1 X120.796 Y116.89 E.01191
G1 X120.396 Y116.89 E.01191
G1 X119.996 Y116.89 E.01191
G1 F2654.999
G1 X119.596 Y116.89 E.01191
G1 F2054.8
G1 X119.409 Y116.89 E.00558
M106 S61.2
M106 S127.5
G1 F1800
G1 X119.409 Y112.31 E.13642
M106 S61.2
M106 S127.5
G1 F2054.8
G1 X119.596 Y112.31 E.00558
M106 S61.2
G1 F2654.999
G1 X119.996 Y112.31 E.01191
G1 F3077
G1 X120.396 Y112.31 E.01191
G1 X120.796 Y112.31 E.01191
G1 X121.196 Y112.31 E.01191
G1 X121.596 Y112.31 E.01191
G1 X121.996 Y112.31 E.01191
G1 X122.396 Y112.31 E.01191
G1 X122.796 Y112.31 E.01191
G1 X123.196 Y112.31 E.01191
G1 X123.596 Y112.31 E.01191
G1 X123.996 Y112.31 E.01191
G1 X158.79 Y112.31 E1.03638
G1 X158.79 Y116.89 E.13642
M106 S127.5
G1 X156.442 Y116.89 E.06995
G1 X156.442 Y174.51 E1.7163
G1 X157.208 Y174.51 E.02283
G1 X157.208 Y176.09 E.04706
G1 X152.792 Y176.09 E.13153
G1 X152.792 Y174.51 E.04706
G1 X153.558 Y174.51 E.02283
G1 X153.558 Y116.89 E1.7163
G1 X142.502 Y116.89 E.32935
; WIPE_START
G1 F12000
M204 S8000
G1 X142.5 Y117.89 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I1.033 J-.643 P1  F60000
G1 X141 Y115.48 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.1065
G1 F15000
M204 S8000
G1 X141 Y174.68 E.29732
; WIPE_START
G1 X141 Y173.68 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I-.087 J1.214 P1  F60000
G1 X155 Y174.68 Z2.4
G1 Z2
G1 E.4 F1800
G1 F15000
M204 S8000
G1 X155 Y115.48 E.29732
; WIPE_START
G1 X155 Y116.48 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I1.2 J.204 P1  F60000
G1 X155.373 Y114.292 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X154.945 Y113.864 E.01945
G1 X154.712 Y113.864 E.00749
G1 X154.574 Y114.292 E.01445
G1 X156.17 Y113.864 E.05313
G1 X155.989 Y113.864 E.00581
G1 X155.875 Y114.292 E.01424
G1 X157.117 Y114.292 E.03995
G1 X156.689 Y113.864 E.01945
G1 X157.236 Y113.864 E.01756
G1 X157.236 Y114.207 E.01102
M204 S10000
G1 X157.134 Y114.988 F60000
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.53531
G1 F10966.917
M204 S8000
G1 X157.134 Y114.742 E.00958
G1 X155.656 Y114.742 E.05751
; LINE_WIDTH: 0.518357
G1 F11357.98
G1 X155.523 Y114.725 E.00503
; LINE_WIDTH: 0.48445
G1 F12000
G1 X155.39 Y114.708 E.00467
; LINE_WIDTH: 0.437097
G1 X155.257 Y114.691 E.00417
G1 X154.743 Y114.691 E.016
; LINE_WIDTH: 0.450542
G1 X154.61 Y114.708 E.00431
; LINE_WIDTH: 0.484445
G1 X154.477 Y114.725 E.00467
; LINE_WIDTH: 0.534935
G1 F10975.291
G1 X154.344 Y114.742 E.00521
G1 X151.733 Y114.742 E.10149
G1 X151.733 Y115.234 E.01914
G1 X154.511 Y115.234 E.10795
G1 X154.544 Y115.132 E.00416
; LINE_WIDTH: 0.518349
G1 F11358.179
G1 X154.61 Y115.115 E.00258
; LINE_WIDTH: 0.484445
G1 F12000
G1 X154.677 Y115.098 E.00239
; LINE_WIDTH: 0.435587
G1 X154.743 Y115.081 E.00213
G1 X155.257 Y115.081 E.01594
; LINE_WIDTH: 0.450544
G1 X155.323 Y115.098 E.00221
; LINE_WIDTH: 0.48445
G1 X155.39 Y115.115 E.00239
; LINE_WIDTH: 0.534731
G1 F10979.838
G1 X155.456 Y115.132 E.00266
G1 X155.489 Y115.234 E.00415
G1 X157.134 Y115.234 E.0639
G1 X157.134 Y115.048 E.00723
; WIPE_START
G1 X157.134 Y115.234 E-.07076
G1 X156.32 Y115.234 E-.30924
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I.529 J-1.096 P1  F60000
G1 X154.371 Y114.292 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X153.628 Y114.292 E.02388
G1 X153.2 Y113.864 E.01945
G1 X153.435 Y113.864 E.00755
G1 X153.32 Y114.292 E.01424
G1 X152.247 Y114.292 E.03452
M204 S10000
G1 X152.997 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X152.158 Y113.864 E.02698
G1 X152.043 Y114.292 E.01424
G1 X151.883 Y114.292 E.00514
G1 X151.404 Y113.864 E.02066
G1 X145.949 Y115.336 E.18168
G1 X144.495 Y113.864 E.0665
G1 X144.381 Y114.292 E.01424
G3 X144.595 Y114.412 I.047 J.167 E.00877
G1 X146.638 Y113.864 E.068
G1 X147.05 Y113.864 E.01325
G1 X146.655 Y115.336 E.04897
; WIPE_START
G1 X146.914 Y114.37 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I.718 J-.983 P1  F60000
G1 X146.222 Y113.864 Z2.4
G1 Z2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X147.693 Y115.336 E.0669
G1 X147.933 Y115.336 E.00769
G1 X148.327 Y113.864 E.04897
G1 X147.967 Y113.864 E.01157
G1 X149.438 Y115.336 E.0669
G1 X149.21 Y115.336 E.00734
G1 X149.604 Y113.864 E.04897
G1 X149.711 Y113.864 E.00346
G1 X151.182 Y115.336 E.0669
G1 X151.284 Y115.336 E.00325
G1 X151.284 Y115.174 E.0052
G3 X150.487 Y115.336 I-.7 J-1.406 E.02645
G1 X150.881 Y113.864 E.04897
; WIPE_START
G1 X150.622 Y114.83 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I.238 J-1.194 P1  F60000
G1 X145.773 Y113.864 Z2.4
G1 Z2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X145.378 Y115.336 E.04897
G1 X144.716 Y115.336 E.02129
G1 X144.716 Y114.565 E.02478
M204 S10000
G1 X144.267 Y114.742 F60000
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.53531
G1 F10966.917
M204 S8000
G1 X141.656 Y114.742 E.10157
; LINE_WIDTH: 0.518357
G1 F11357.98
G1 X141.523 Y114.725 E.00503
; LINE_WIDTH: 0.48445
G1 F12000
G1 X141.39 Y114.708 E.00467
; LINE_WIDTH: 0.437097
G1 X141.257 Y114.691 E.00417
G1 X140.743 Y114.691 E.016
; LINE_WIDTH: 0.450542
G1 X140.61 Y114.708 E.00431
; LINE_WIDTH: 0.484445
G1 X140.477 Y114.725 E.00467
; LINE_WIDTH: 0.534929
G1 F10975.408
G1 X140.344 Y114.742 E.00521
G1 X137.733 Y114.742 E.10149
G1 X137.733 Y115.234 E.01914
G1 X140.511 Y115.234 E.10795
G1 X140.544 Y115.132 E.00416
; LINE_WIDTH: 0.518349
G1 F11358.179
G1 X140.61 Y115.115 E.00258
; LINE_WIDTH: 0.484445
G1 F12000
G1 X140.677 Y115.098 E.00239
; LINE_WIDTH: 0.435587
G1 X140.743 Y115.081 E.00213
G1 X141.257 Y115.081 E.01594
; LINE_WIDTH: 0.450544
G1 X141.323 Y115.098 E.00221
; LINE_WIDTH: 0.48445
G1 X141.39 Y115.115 E.00239
; LINE_WIDTH: 0.534967
G1 F10974.571
G1 X141.456 Y115.132 E.00267
G1 X141.489 Y115.234 E.00416
G1 X144.267 Y115.234 E.10796
G1 X144.267 Y114.802 E.01681
M204 S10000
G1 X144.274 Y113.864 F60000
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X143.218 Y113.864 E.03395
G1 X143.104 Y114.292 E.01424
G1 X143.161 Y114.292 E.00183
G1 X142.733 Y113.864 E.01945
G1 X142.145 Y113.864 E.01892
; WIPE_START
G1 X142.733 Y113.864 E-.22358
G1 X143.024 Y114.156 E-.15642
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I.172 J-1.205 P1  F60000
G1 X140.989 Y113.864 Z2.4
G1 Z2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X141.416 Y114.292 E.01945
G1 X141.827 Y114.292 E.0132
G1 X141.941 Y113.864 E.01424
G1 X140.276 Y114.292 E.0553
G1 X140.55 Y114.292 E.00881
G1 X140.664 Y113.864 E.01424
G1 X139.591 Y113.864 E.03452
M204 S10000
G1 X139.041 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X138.11 Y113.864 E.02992
G1 X137.995 Y114.292 E.01424
G1 X137.927 Y114.292 E.00219
G1 X137.5 Y113.864 E.01945
G1 X137.907 Y113.864 E.01308
M204 S10000
G1 X138.199 Y114.292 F60000
G1 F13265.217
M204 S8000
G1 X139.273 Y114.292 E.03452
G1 X139.387 Y113.864 E.01424
G1 X139.244 Y113.864 E.0046
G1 X139.672 Y114.292 E.01945
G1 X140.072 Y114.292 E.01288
; WIPE_START
G1 X139.672 Y114.292 E-.15217
G1 X139.248 Y113.868 E-.22783
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I.001 J-1.217 P1  F60000
G1 X133.807 Y113.864 Z2.4
G1 Z2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X133.002 Y113.864 E.0259
G1 X132.608 Y115.336 E.04897
M204 S10000
G1 X131.819 Y115.336 F60000
G1 F13265.217
M204 S8000
G1 X131.993 Y115.336 E.00559
G1 X130.521 Y113.864 E.0669
G1 X130.448 Y113.864 E.00238
G1 X130.053 Y115.336 E.04897
G1 X130.248 Y115.336 E.00626
G1 X128.777 Y113.864 E.0669
G1 X129.17 Y113.864 E.01265
G1 X128.776 Y115.336 E.04897
G1 X128.504 Y115.336 E.00877
G1 X127.032 Y113.864 E.0669
M204 S10000
G1 X126.616 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X126.222 Y115.336 E.04897
G1 X125.218 Y115.336 E.03229
M204 S10000
G1 X124.741 Y115.336 F60000
G1 F13265.217
M204 S8000
M73 P59 R6
G1 X123.668 Y115.336 E.03452
G1 X124.062 Y113.864 E.04897
G1 X123.543 Y113.864 E.01668
G1 X125.014 Y115.336 E.0669
G1 X124.945 Y115.336 E.00223
G1 X125.339 Y113.864 E.04897
G1 X125.288 Y113.864 E.00165
G1 X126.759 Y115.336 E.0669
G1 X126.849 Y115.336 E.0029
G1 X132.339 Y113.864 E.18277
G1 X132.266 Y113.864 E.00236
G1 X133.737 Y115.336 E.0669
G1 X133.885 Y115.336 E.00474
G1 X134.279 Y113.864 E.04897
G1 X134.011 Y113.864 E.00863
G1 X135.482 Y115.336 E.0669
G1 X135.162 Y115.336 E.01029
G1 X135.556 Y113.864 E.04897
G1 X135.755 Y113.864 E.00641
G1 X137.284 Y115.336 E.06822
G1 X137.284 Y115.094 E.00777
G1 X136.381 Y115.336 E.03003
G1 X136.439 Y115.336 E.00184
G1 X136.833 Y113.864 E.04897
G1 X137.105 Y113.864 E.00876
G1 X131.615 Y115.336 E.18277
G1 X131.33 Y115.336 E.00916
G1 X131.725 Y113.864 E.04897
; WIPE_START
G1 X131.466 Y114.83 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I-.154 J-1.207 P1  F60000
G1 X127.499 Y115.336 Z2.4
G1 Z2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X127.893 Y113.864 E.04897
G1 X127.573 Y113.864 E.0103
G1 X122.083 Y115.336 E.18277
G1 X122.391 Y115.336 E.0099
G1 X122.807 Y113.864 E.04916
G1 X120.963 Y114.358 E.06137
G1 X120.963 Y114.774 E.01335
G1 X121.525 Y115.336 E.02555
G1 X121.114 Y115.336 E.01324
G1 X121.508 Y113.864 E.04897
G1 X120.963 Y113.864 E.01751
G1 X120.963 Y114.155 E.00934
M204 S10000
G1 X121.799 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X123.27 Y115.336 E.0669
; COOLING_NODE: 0
; WIPE_START
G1 X122.563 Y114.628 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I-.177 J-1.204 P1  F60000
G1 X115.385 Y115.684 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Inner wall
G1 F13265.217
M204 S8000
G1 X112.416 Y115.684 E.09546
G1 X112.416 Y113.516 E.0697
G1 X115.385 Y113.516 E.09546
G1 X115.385 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X115.792 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X112.009 Y116.091 E.12164
G1 X112.009 Y113.109 E.09588
G1 X115.792 Y113.109 E.12164
G1 X115.792 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X116.199 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X111.602 Y116.498 E.14782
G1 X111.602 Y112.702 E.12206
G1 X116.199 Y112.702 E.14782
G1 X116.199 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X116.404 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F3077
M204 S5000
G1 X111.21 Y116.89 E.1547
G1 X111.21 Y112.31 E.13642
G1 X112.004 Y112.31 E.02364
G1 X112.404 Y112.31 E.01191
G1 X112.804 Y112.31 E.01191
G1 X113.204 Y112.31 E.01191
G1 X113.604 Y112.31 E.01191
G1 X114.004 Y112.31 E.01191
G1 X114.404 Y112.31 E.01191
G1 X114.804 Y112.31 E.01191
G1 X115.204 Y112.31 E.01191
G1 X115.604 Y112.31 E.01191
G1 X116.004 Y112.31 E.01191
G1 F2654.983
G1 X116.404 Y112.31 E.01191
G1 F2054.786
G1 X116.591 Y112.31 E.00558
M106 S61.2
M106 S127.5
G1 F1800
G1 X116.591 Y116.89 E.13642
M106 S61.2
M106 S127.5
G1 F1971.381
G1 X116.464 Y116.89 E.0038
M106 S61.2
; WIPE_START
M204 S8000
G1 X115.464 Y116.89 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.4 I1.167 J-.344 P1  F60000
G1 X114.993 Y115.292 Z2.4
G1 Z2
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X114.993 Y113.908 E.04121
G1 X112.808 Y113.908 E.06507
G1 X112.808 Y115.292 E.04121
G1 X114.933 Y115.292 E.06328
M204 S10000
G1 X114.553 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X114.553 Y114.348 E.02
G1 X113.248 Y114.348 E.05184
G1 X113.248 Y114.852 E.02
G1 X114.493 Y114.852 E.04945
M106 S127.5
; CHANGE_LAYER
; Z_HEIGHT: 2.2
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F10731.32
G1 X113.493 Y114.852 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M106 S51
M625
; layer num/total_layer_count: 11/27
; update layer progress
M73 L11
M991 S0 P10 ;notify layer change
M106 S127.5
; OBJECT_ID: 16
; COOLING_NODE: 0
; start printing object, unique label id: 16
M624 BAAAAAAAAAA=
M106 S127.5
M204 S10000
G17
G3 Z2.4 I-.747 J.961 P1  F60000
G1 X195.214 Y178.407 Z2.4
G1 Z2.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X195.085 Y178.413 E.00414
G3 X194.575 Y171.609 I-.085 J-3.415 E.33412
G1 X194.915 Y171.583 E.01096
G3 X195.425 Y178.387 I.085 J3.415 E.33411
G1 X195.273 Y178.402 E.00488
; COOLING_NODE: 0
M204 S10000
G1 X195.183 Y178.001 F60000
G1 F13265.217
M204 S8000
G1 X195.075 Y178.006 E.00349
G3 X194.626 Y172.013 I-.075 J-3.008 E.29427
G1 X194.925 Y171.991 E.00966
G3 X195.374 Y177.983 I.075 J3.008 E.29427
G1 X195.243 Y177.996 E.00423
; COOLING_NODE: 0
M204 S10000
G1 X195.153 Y177.595 F60000
G1 F13265.217
M204 S8000
G1 X195.065 Y177.599 E.00283
G3 X194.676 Y172.417 I-.065 J-2.6 E.25443
G1 X194.935 Y172.398 E.00835
G3 X195.323 Y177.579 I.065 J2.6 E.25443
G1 X195.213 Y177.59 E.00358
; COOLING_NODE: 0
M204 S250
G1 X195.123 Y177.201 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X195.055 Y177.207 E.00203
G3 X194.725 Y172.807 I-.055 J-2.208 E.20014
G1 X194.945 Y172.79 E.00657
G3 X195.491 Y177.152 I.055 J2.208 E.19358
G1 X195.182 Y177.193 E.00928
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X195.055 Y177.207 E-.0487
G1 X194.616 Y177.177 E-.16713
G1 X194.2 Y177.06 E-.16418
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I-1.085 J.551 P1  F60000
G1 X201.584 Y191.584 Z2.6
G1 Z2.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y191.584 E.42342
G1 X188.416 Y170.416 E.68067
G1 X201.584 Y170.416 E.42342
G1 X201.584 Y191.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y191.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y191.991 E.4496
G1 X188.009 Y170.009 E.70685
G1 X201.991 Y170.009 E.4496
G1 X201.991 Y191.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y192.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y192.398 E.47578
G1 X187.602 Y169.602 E.73303
G1 X202.398 Y169.602 E.47578
G1 X202.398 Y192.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y192.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y192.79 E.46408
G1 X187.21 Y169.21 E.70237
G1 X202.79 Y169.21 E.46408
G1 X202.79 Y192.73 E.70058
; object ids of layer 11 start: 8,12,16
M624 BwAAAAAAAAA=
M106 S127.5
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer11 end: 8,12,16
M106 S51
M625
; WIPE_START
M204 S8000
G1 X201.79 Y192.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I.872 J-.849 P1  F60000
G1 X200.506 Y191.417 Z2.6
G1 Z2.2
G1 E.4 F1800
; FEATURE: Bridge
; LINE_WIDTH: 0.40036
; LAYER_HEIGHT: 0.4
G1 F3000
M204 S8000
G1 X201.214 Y190.709 E.04978
G1 X201.214 Y190.072 E.03167
G1 X200.072 Y191.214 E.08033
G1 X199.435 Y191.214 E.03167
G1 X201.214 Y189.435 E.12511
G1 X201.214 Y188.798 E.03167
G1 X198.798 Y191.214 E.1699
G1 X198.161 Y191.214 E.03167
G1 X201.214 Y188.161 E.21468
G1 X201.214 Y187.524 E.03167
G1 X197.524 Y191.214 E.25947
G1 X196.887 Y191.214 E.03167
G1 X201.214 Y186.887 E.30425
G1 X201.214 Y186.25 E.03167
G1 X196.25 Y191.214 E.34904
G1 X195.613 Y191.214 E.03167
G1 X201.214 Y185.613 E.39383
G1 X201.214 Y184.976 E.03167
G1 X194.977 Y191.214 E.43861
G1 X194.34 Y191.214 E.03167
G1 X201.214 Y184.34 E.4834
G1 X201.214 Y183.703 E.03167
G1 X193.703 Y191.214 E.52818
G1 X193.066 Y191.214 E.03167
G1 X201.214 Y183.066 E.57297
G1 X201.214 Y182.429 E.03167
G1 X192.429 Y191.214 E.61775
G1 X191.792 Y191.214 E.03167
G1 X201.214 Y181.792 E.66254
G1 X201.214 Y181.155 E.03167
G1 X191.155 Y191.214 E.70732
G1 X190.518 Y191.214 E.03167
G1 X201.214 Y180.518 E.75211
G1 X201.214 Y179.881 E.03167
G1 X189.881 Y191.214 E.7969
G1 X189.244 Y191.214 E.03167
G1 X201.214 Y179.244 E.84168
G1 X201.214 Y178.607 E.03167
G1 X188.786 Y191.036 E.87392
M73 P60 R6
G1 X188.786 Y190.399 E.03167
G1 X201.214 Y177.971 E.87392
G1 X201.214 Y177.334 E.03167
G1 X188.786 Y189.762 E.87392
G1 X188.786 Y189.125 E.03167
G1 X201.214 Y176.697 E.87392
G1 X201.214 Y176.06 E.03167
G1 X188.786 Y188.488 E.87392
G1 X188.786 Y187.851 E.03167
G1 X201.214 Y175.423 E.87392
G1 X201.214 Y174.786 E.03167
G1 X188.786 Y187.214 E.87392
G1 X188.786 Y186.577 E.03167
G1 X201.214 Y174.149 E.87392
G1 X201.214 Y173.512 E.03167
G1 X198.623 Y176.103 E.18217
G2 X198.772 Y175.317 I-4.297 J-1.222 E.03982
G1 X201.214 Y172.875 E.1717
G1 X201.214 Y172.238 E.03167
G1 X198.772 Y174.68 E.17171
G2 X198.683 Y174.132 I-4.457 J.443 E.02762
G1 X201.214 Y171.601 E.17796
G1 X201.214 Y170.965 E.03167
G1 X198.533 Y173.645 E.18851
G2 X198.335 Y173.206 I-2.292 J.768 E.02399
G1 X200.756 Y170.786 E.17019
G1 X200.119 Y170.786 E.03167
G1 X198.091 Y172.814 E.14262
G2 X197.805 Y172.463 I-1.899 J1.254 E.02255
G1 X199.482 Y170.786 E.11793
G1 X198.845 Y170.786 E.03167
G1 X197.485 Y172.147 E.09567
G2 X197.126 Y171.868 I-2.402 J2.73 E.02259
G1 X198.208 Y170.786 E.07612
G1 X197.571 Y170.786 E.03167
G1 X196.721 Y171.627 E.05946
G2 X196.281 Y171.439 I-2.383 J4.972 E.0238
G1 X196.934 Y170.786 E.04593
G1 X196.297 Y170.786 E.03167
G1 X195.785 Y171.298 E.03604
G2 X195.231 Y171.216 I-.69 J2.728 E.02791
G1 X195.661 Y170.786 E.03023
G1 X195.024 Y170.786 E.03167
G1 X194.572 Y171.238 E.03179
G2 X193.744 Y171.428 I.186 J2.7 E.04239
G1 X194.387 Y170.786 E.04518
G1 X193.75 Y170.786 E.03167
G1 X188.786 Y175.75 E.34905
G1 X188.786 Y176.387 E.03167
G1 X191.439 Y173.734 E.18655
G2 X191.238 Y174.571 I3.354 J1.245 E.04291
G1 X188.786 Y177.024 E.17246
G1 X188.786 Y177.661 E.03167
G1 X191.223 Y175.224 E.17137
G2 X191.296 Y175.787 I4.627 J-.315 E.02828
G1 X188.786 Y178.297 E.17652
G1 X188.786 Y178.934 E.03167
G1 X191.44 Y176.281 E.18661
G2 X191.632 Y176.726 I2.37 J-.758 E.02414
G1 X188.786 Y179.571 E.2001
G1 X188.786 Y180.208 E.03167
G1 X191.866 Y177.128 E.21661
G2 X192.145 Y177.486 I5.985 J-4.376 E.02257
G1 X188.786 Y180.845 E.23622
G1 X188.786 Y181.482 E.03167
G1 X192.462 Y177.806 E.25848
G2 X192.816 Y178.089 I1.591 J-1.626 E.02257
G1 X188.786 Y182.119 E.28335
G1 X188.786 Y182.756 E.03167
G1 X193.208 Y178.334 E.31093
G2 X193.643 Y178.535 I2.653 J-5.162 E.02386
G1 X188.786 Y183.393 E.34155
G1 X188.786 Y184.03 E.03167
G1 X194.133 Y178.683 E.37597
G2 X194.68 Y178.773 I.922 J-3.894 E.02758
G1 X188.786 Y184.667 E.41443
G1 X188.786 Y185.303 E.03167
G1 X195.319 Y178.77 E.45941
G2 X196.108 Y178.619 I-.329 J-3.84 E.03998
G1 X188.583 Y186.143 E.52908
M106 S51
M106 S127.5
; WIPE_START
G1 X189.291 Y185.436 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I1.214 J-.085 P1  F60000
G1 X188.583 Y175.315 Z2.6
G1 Z2.2
G1 E.4 F1800
G1 F3000
M204 S8000
G1 X193.113 Y170.786 E.3185
G1 X192.476 Y170.786 E.03167
G1 X188.786 Y174.476 E.25948
G1 X188.786 Y173.839 E.03167
G1 X191.839 Y170.786 E.21469
G1 X191.202 Y170.786 E.03167
G1 X188.786 Y173.202 E.16991
G1 X188.786 Y172.565 E.03167
G1 X190.565 Y170.786 E.12512
G1 X189.928 Y170.786 E.03167
G1 X188.786 Y171.928 E.08034
G1 X188.786 Y171.292 E.03167
G1 X189.494 Y170.583 E.04979
M106 S51
M106 S127.5
; OBJECT_ID: 12
; COOLING_NODE: 0
; WIPE_START
G1 X188.787 Y171.291 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 16
M106 S51
M625
; start printing object, unique label id: 12
M624 AgAAAAAAAAA=
M106 S127.5
M204 S10000
G17
G3 Z2.6 I1.201 J.194 P1  F60000
G1 X197.493 Y117.333 Z2.6
G1 Z2.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
; LAYER_HEIGHT: 0.2
G1 F13265.217
M204 S8000
G1 X197.43 Y117.399 E.00295
G3 X194.575 Y111.609 I-2.43 J-2.401 E.4183
G1 X194.915 Y111.583 E.01096
G3 X197.618 Y117.192 I.085 J3.415 E.2519
G1 X197.533 Y117.288 E.00411
; COOLING_NODE: 0
M204 S10000
G1 X197.194 Y117.057 F60000
G1 F13265.217
M204 S8000
G1 X197.139 Y117.113 E.00251
G3 X194.626 Y112.013 I-2.139 J-2.115 E.36838
G1 X194.925 Y111.991 E.00966
G3 X197.305 Y116.931 I.075 J3.008 E.22188
G1 X197.233 Y117.012 E.00349
; COOLING_NODE: 0
M204 S10000
G1 X196.904 Y116.764 F60000
G1 F13265.217
M204 S8000
G1 X196.849 Y116.828 E.00272
G3 X194.676 Y112.417 I-1.849 J-1.83 E.31847
G1 X194.935 Y112.398 E.00835
G3 X197.148 Y116.465 I.065 J2.6 E.18358
G1 X196.942 Y116.718 E.01049
; COOLING_NODE: 0
M204 S250
G1 X196.603 Y116.515 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X196.569 Y116.553 E.00152
G3 X194.725 Y112.807 I-1.569 J-1.555 E.25047
G1 X194.945 Y112.79 E.00657
G3 X196.824 Y116.244 I.055 J2.208 E.1444
G1 X196.641 Y116.469 E.00864
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X196.569 Y116.553 E-.04217
G1 X196.29 Y116.795 E-.14017
G1 X195.909 Y117.015 E-.16728
G1 X195.833 Y117.04 E-.03038
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I-1.132 J.447 P1  F60000
G1 X201.584 Y131.584 Z2.6
G1 Z2.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y131.584 E.42342
G1 X188.416 Y110.416 E.68067
G1 X201.584 Y110.416 E.42342
G1 X201.584 Y131.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y131.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y131.991 E.4496
G1 X188.009 Y110.009 E.70685
G1 X201.991 Y110.009 E.4496
G1 X201.991 Y131.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y132.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y132.398 E.47578
G1 X187.602 Y109.602 E.73303
G1 X202.398 Y109.602 E.47578
M73 P61 R6
G1 X202.398 Y132.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y132.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y132.79 E.46408
G1 X187.21 Y109.21 E.70237
G1 X202.79 Y109.21 E.46408
G1 X202.79 Y132.73 E.70058
; WIPE_START
M204 S8000
G1 X201.79 Y132.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I.872 J-.849 P1  F60000
G1 X200.506 Y131.417 Z2.6
G1 Z2.2
G1 E.4 F1800
; FEATURE: Bridge
; LINE_WIDTH: 0.40036
; LAYER_HEIGHT: 0.4
G1 F3000
M204 S8000
G1 X201.214 Y130.709 E.04978
G1 X201.214 Y130.072 E.03167
G1 X200.072 Y131.214 E.08033
G1 X199.435 Y131.214 E.03167
G1 X201.214 Y129.435 E.12511
G1 X201.214 Y128.798 E.03167
G1 X198.798 Y131.214 E.1699
G1 X198.161 Y131.214 E.03167
G1 X201.214 Y128.161 E.21468
G1 X201.214 Y127.524 E.03167
G1 X197.524 Y131.214 E.25947
G1 X196.887 Y131.214 E.03167
G1 X201.214 Y126.887 E.30425
G1 X201.214 Y126.25 E.03167
G1 X196.25 Y131.214 E.34904
G1 X195.613 Y131.214 E.03167
G1 X201.214 Y125.613 E.39383
G1 X201.214 Y124.976 E.03167
G1 X194.977 Y131.214 E.43861
G1 X194.34 Y131.214 E.03167
G1 X201.214 Y124.34 E.4834
G1 X201.214 Y123.703 E.03167
G1 X193.703 Y131.214 E.52818
G1 X193.066 Y131.214 E.03167
G1 X201.214 Y123.066 E.57297
G1 X201.214 Y122.429 E.03167
G1 X192.429 Y131.214 E.61775
G1 X191.792 Y131.214 E.03167
G1 X201.214 Y121.792 E.66254
G1 X201.214 Y121.155 E.03167
G1 X191.155 Y131.214 E.70732
G1 X190.518 Y131.214 E.03167
G1 X201.214 Y120.518 E.75211
G1 X201.214 Y119.881 E.03167
G1 X189.881 Y131.214 E.7969
G1 X189.244 Y131.214 E.03167
G1 X201.214 Y119.244 E.84168
M73 P61 R5
G1 X201.214 Y118.607 E.03167
G1 X188.786 Y131.036 E.87392
G1 X188.786 Y130.399 E.03167
G1 X201.214 Y117.971 E.87392
G1 X201.214 Y117.334 E.03167
G1 X188.786 Y129.762 E.87392
G1 X188.786 Y129.125 E.03167
G1 X201.214 Y116.697 E.87392
G1 X201.214 Y116.06 E.03167
G1 X188.786 Y128.488 E.87392
G1 X188.786 Y127.851 E.03167
G1 X201.214 Y115.423 E.87392
G1 X201.214 Y114.786 E.03167
G1 X188.786 Y127.214 E.87392
G1 X188.786 Y126.577 E.03167
G1 X201.214 Y114.149 E.87392
G1 X201.214 Y113.512 E.03167
G1 X198.623 Y116.103 E.18217
G2 X198.772 Y115.317 I-4.296 J-1.222 E.03982
G1 X201.214 Y112.875 E.1717
G1 X201.214 Y112.238 E.03167
G1 X198.772 Y114.68 E.17171
G2 X198.683 Y114.132 I-4.458 J.443 E.02762
G1 X201.214 Y111.601 E.17796
G1 X201.214 Y110.965 E.03167
G1 X198.533 Y113.645 E.18851
G2 X198.335 Y113.206 I-2.288 J.766 E.02399
G1 X200.756 Y110.786 E.17019
G1 X200.119 Y110.786 E.03167
G1 X198.091 Y112.814 E.14262
G2 X197.806 Y112.462 I-1.9 J1.242 E.02256
G1 X199.482 Y110.786 E.11784
G1 X198.845 Y110.786 E.03167
G1 X197.485 Y112.146 E.09567
G2 X197.126 Y111.868 I-1.567 J1.652 E.02261
G1 X198.208 Y110.786 E.07612
G1 X197.571 Y110.786 E.03167
G1 X196.728 Y111.629 E.05928
G2 X196.281 Y111.439 I-1.173 J2.14 E.02419
G1 X196.934 Y110.786 E.04593
G1 X196.297 Y110.786 E.03167
G1 X195.785 Y111.298 E.03604
G2 X195.231 Y111.216 I-1.27 J6.627 E.02787
G1 X195.661 Y110.786 E.03023
G1 X195.024 Y110.786 E.03167
G1 X194.572 Y111.238 E.03179
G2 X193.744 Y111.428 I.716 J5.002 E.04226
G1 X194.387 Y110.786 E.04518
G1 X193.75 Y110.786 E.03167
G1 X188.786 Y115.75 E.34905
G1 X188.786 Y116.387 E.03167
G1 X191.439 Y113.734 E.18655
G2 X191.238 Y114.571 I3.353 J1.245 E.04291
G1 X188.786 Y117.024 E.17246
G1 X188.786 Y117.661 E.03167
G1 X191.223 Y115.224 E.17137
G2 X191.296 Y115.787 I4.627 J-.315 E.02828
G1 X188.786 Y118.297 E.17652
G1 X188.786 Y118.934 E.03167
M73 P62 R5
G1 X191.44 Y116.28 E.18661
G2 X191.632 Y116.726 I2.315 J-.734 E.02414
G1 X188.786 Y119.571 E.2001
G1 X188.786 Y120.208 E.03167
G1 X191.866 Y117.128 E.2166
G2 X192.145 Y117.486 I6.02 J-4.403 E.02257
G1 X188.786 Y120.845 E.23622
G1 X188.786 Y121.482 E.03167
G1 X192.462 Y117.806 E.25848
G2 X192.816 Y118.089 I1.594 J-1.628 E.02257
G1 X188.786 Y122.119 E.28335
G1 X188.786 Y122.756 E.03167
G1 X193.208 Y118.334 E.31093
G2 X193.643 Y118.535 I2.665 J-5.188 E.02386
G1 X188.786 Y123.393 E.34155
G1 X188.786 Y124.03 E.03167
G1 X194.133 Y118.683 E.37598
G2 X194.68 Y118.773 I.724 J-2.692 E.0276
G1 X188.786 Y124.667 E.41443
G1 X188.786 Y125.303 E.03167
G1 X195.319 Y118.77 E.45941
G2 X196.108 Y118.619 I-.332 J-3.858 E.03998
G1 X188.583 Y126.143 E.52908
M106 S51
M106 S127.5
; WIPE_START
G1 X189.291 Y125.436 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I1.214 J-.085 P1  F60000
G1 X188.583 Y115.315 Z2.6
G1 Z2.2
G1 E.4 F1800
G1 F3000
M204 S8000
G1 X193.113 Y110.786 E.3185
G1 X192.476 Y110.786 E.03167
G1 X188.786 Y114.476 E.25948
G1 X188.786 Y113.839 E.03167
G1 X191.839 Y110.786 E.21469
G1 X191.202 Y110.786 E.03167
G1 X188.786 Y113.202 E.16991
G1 X188.786 Y112.565 E.03167
G1 X190.565 Y110.786 E.12512
G1 X189.928 Y110.786 E.03167
G1 X188.786 Y111.928 E.08034
G1 X188.786 Y111.292 E.03167
G1 X189.494 Y110.583 E.04979
M106 S51
; OBJECT_ID: 8
; COOLING_NODE: 0
; WIPE_START
G1 X188.787 Y111.291 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 12
M625
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z2.6 I-.111 J-1.212 P1  F60000
G1 X141.015 Y115.684 Z2.6
G1 Z2.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
; LAYER_HEIGHT: 0.2
G1 F13265.217
M204 S8000
G1 X120.287 Y115.684 E.66655
G1 X120.287 Y113.516 E.0697
G1 X157.584 Y113.516 E1.19934
G1 X157.584 Y115.684 E.0697
G1 X141.075 Y115.684 E.53086
; COOLING_NODE: 0
M204 S10000
G1 X141.422 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X141.422 Y175.291 E1.90366
G1 X140.578 Y175.291 E.02715
G1 X140.578 Y116.091 E1.90366
G1 X119.879 Y116.091 E.66558
G1 X119.879 Y113.109 E.09588
G1 X157.991 Y113.109 E1.22552
G1 X157.991 Y116.091 E.09588
G1 X155.422 Y116.091 E.0826
G1 X155.422 Y175.291 E1.90366
G1 X154.578 Y175.291 E.02715
G1 X154.578 Y116.091 E1.90366
G1 X141.482 Y116.091 E.42111
; COOLING_NODE: 0
M204 S10000
G1 X141.829 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X141.829 Y174.902 E1.87806
G1 X142.671 Y174.902 E.02705
G1 X142.671 Y175.698 E.02559
G1 X139.329 Y175.698 E.10744
G1 X139.329 Y174.902 E.02559
G1 X140.171 Y174.902 E.02705
G1 X140.171 Y116.498 E1.87806
G1 X119.472 Y116.498 E.66558
G1 X119.472 Y112.702 E.12206
G1 X158.398 Y112.702 E1.2517
G1 X158.398 Y116.498 E.12206
G1 X155.829 Y116.498 E.0826
G1 X155.829 Y174.902 E1.87806
G1 X156.671 Y174.902 E.02705
G1 X156.671 Y175.698 E.02559
G1 X153.329 Y175.698 E.10744
G1 X153.329 Y174.902 E.02559
G1 X154.171 Y174.902 E.02705
G1 X154.171 Y116.498 E1.87806
G1 X141.889 Y116.498 E.39493
; COOLING_NODE: 0
M204 S250
G1 X142.221 Y116.89 F60000
M106 S127.5
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F2945
M204 S5000
G1 X142.221 Y174.51 E1.7163
G1 X143.063 Y174.51 E.02506
G1 X143.063 Y176.09 E.04706
G1 X138.937 Y176.09 E.12288
G1 X138.937 Y174.51 E.04706
G1 X139.779 Y174.51 E.02506
G1 X139.779 Y116.89 E1.7163
G1 X124.968 Y116.89 E.44116
G1 X124.568 Y116.89 E.01191
M73 P63 R5
G1 X124.168 Y116.89 E.01191
G1 X123.768 Y116.89 E.01191
G1 X123.368 Y116.89 E.01191
G1 X122.968 Y116.89 E.01191
G1 X122.568 Y116.89 E.01191
G1 X122.168 Y116.89 E.01191
G1 X121.768 Y116.89 E.01191
G1 X121.368 Y116.89 E.01191
G1 X120.968 Y116.89 E.01191
G1 F2887.832
G1 X120.568 Y116.89 E.01191
G1 F2260.221
G1 X120.168 Y116.89 E.01191
G1 F1709.41
G1 X119.768 Y116.89 E.01191
G1 F1235.398
G1 X119.368 Y116.89 E.01191
G1 F838.187
G1 X119.08 Y116.89 E.00857
M106 S51
M106 S127.5
G1 F600
G1 X119.08 Y112.31 E.13642
M106 S51
M106 S127.5
G1 F838.187
G1 X119.368 Y112.31 E.00857
M106 S51
G1 F1235.398
G1 X119.768 Y112.31 E.01191
G1 F1709.41
G1 X120.168 Y112.31 E.01191
G1 F2260.221
G1 X120.568 Y112.31 E.01191
G1 F2887.832
G1 X120.968 Y112.31 E.01191
G1 F2945
G1 X121.368 Y112.31 E.01191
G1 X121.768 Y112.31 E.01191
G1 X122.168 Y112.31 E.01191
G1 X122.568 Y112.31 E.01191
G1 X122.968 Y112.31 E.01191
G1 X123.368 Y112.31 E.01191
G1 X123.768 Y112.31 E.01191
G1 X124.168 Y112.31 E.01191
G1 X124.568 Y112.31 E.01191
G1 X124.968 Y112.31 E.01191
G1 X158.79 Y112.31 E1.00744
G1 X158.79 Y116.89 E.13642
G1 X156.221 Y116.89 E.07651
G1 X156.221 Y174.51 E1.7163
G1 X157.063 Y174.51 E.02506
G1 X157.063 Y176.09 E.04706
G1 X152.937 Y176.09 E.12288
G1 X152.937 Y174.51 E.04706
G1 X153.779 Y174.51 E.02506
G1 X153.779 Y116.89 E1.7163
G1 X142.281 Y116.89 E.34247
; WIPE_START
G1 F12000
M204 S8000
G1 X142.28 Y117.89 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I1.025 J-.656 P1  F60000
G1 X141 Y115.887 Z2.6
G1 Z2.2
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.48018
G1 F12349.632
M204 S8000
G1 X141 Y175.087 E2.04479
M204 S10000
G1 X141.626 Y175.3 F60000
; LINE_WIDTH: 0.43172
G1 F13888.888
M204 S8000
G1 X142.467 Y175.3 E.02584
; WIPE_START
G1 X141.626 Y175.3 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I0 J-1.217 P1  F60000
G1 X140.374 Y175.3 Z2.6
G1 Z2.2
G1 E.4 F1800
G1 F13888.888
M204 S8000
G1 X139.533 Y175.3 E.02584
; WIPE_START
G1 X140.374 Y175.3 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I0 J1.217 P1  F60000
G1 X153.533 Y175.3 Z2.6
G1 Z2.2
G1 E.4 F1800
G1 F13888.888
M204 S8000
G1 X154.374 Y175.3 E.02584
M204 S10000
G1 X155 Y175.087 F60000
M106 S127.5
; LINE_WIDTH: 0.48018
G1 F12349.632
M204 S8000
G1 X155 Y115.887 E2.04479
; WIPE_START
G1 X155 Y116.887 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I1.206 J-.16 P1  F60000
G1 X154.655 Y114.292 Z2.6
G1 Z2.2
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X155.121 Y114.292 E.01498
G1 X156.716 Y113.864 E.05313
G1 X156.889 Y113.864 E.00556
G1 X157.236 Y114.211 E.01574
G1 X157.236 Y114.292 E.00262
G1 X157.005 Y114.292 E.0074
G1 X157.12 Y113.864 E.01424
G1 X157.236 Y113.864 E.00372
G1 X157.236 Y114.007 E.00458
M204 S10000
G1 X157.134 Y114.988 F60000
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.5353
G1 F10967.139
M204 S8000
G1 X157.134 Y114.742 E.00958
G1 X151.733 Y114.742 E.21007
G1 X151.733 Y115.234 E.01915
G1 X157.134 Y115.234 E.21007
G1 X157.134 Y115.048 E.00724
; WIPE_START
G1 X157.134 Y115.234 E-.07075
G1 X156.32 Y115.234 E-.30925
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I1.03 J-.648 P1  F60000
G1 X155.728 Y114.292 Z2.6
G1 Z2.2
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X155.843 Y113.864 E.01424
M204 S10000
G1 X155.573 Y114.292 F60000
G1 F13265.217
M204 S8000
G1 X155.145 Y113.864 E.01945
G1 X154.566 Y113.864 E.01862
G1 X154.451 Y114.292 E.01424
G1 X153.828 Y114.292 E.02004
G1 X153.4 Y113.864 E.01945
G1 X153.289 Y113.864 E.00359
G1 X153.174 Y114.292 E.01424
G1 X152.287 Y114.292 E.02853
M204 S10000
G1 X151.747 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X151.656 Y113.864 E.00292
G1 X152.083 Y114.292 E.01945
G1 X151.897 Y114.292 E.006
G1 X152.012 Y113.864 E.01424
G1 X151.95 Y113.864 E.00197
G1 X146.46 Y115.336 E.18277
G1 X146.509 Y115.336 E.00157
G1 X146.903 Y113.864 E.04897
G1 X147.184 Y113.864 E.00903
G1 X144.711 Y114.527 E.08235
G2 X144.234 Y114.292 I-.356 J.12 E.01897
G1 X144.349 Y113.864 E.01424
G1 X144.678 Y113.864 E.01057
G1 X146.149 Y115.336 E.0669
G1 X145.232 Y115.336 E.02948
G1 X145.626 Y113.864 E.04897
G1 X144.881 Y113.864 E.02395
M204 S10000
G1 X144.031 Y114.292 F60000
G1 F13265.217
M204 S8000
G1 X143.361 Y114.292 E.02155
G1 X142.933 Y113.864 E.01945
G1 X143.072 Y113.864 E.00446
G1 X142.957 Y114.292 E.01424
G1 X141.96 Y114.292 E.03207
M204 S10000
G1 X141.68 Y114.292 F60000
G1 F13265.217
M204 S8000
G1 X141.795 Y113.864 E.01424
M204 S10000
G1 X141.616 Y114.292 F60000
G1 F13265.217
M204 S8000
G1 X141.189 Y113.864 E.01945
G1 X140.518 Y113.864 E.02157
G1 X140.403 Y114.292 E.01424
G1 X140.822 Y114.292 E.01347
G1 X142.418 Y113.864 E.05313
G1 X142.73 Y113.864 E.01002
; WIPE_START
G1 X142.418 Y113.864 E-.11843
G1 X141.753 Y114.043 E-.26157
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I-.326 J1.172 P1  F60000
G1 X144.267 Y114.742 Z2.6
G1 Z2.2
G1 E.4 F1800
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.535305
G1 F10967.029
M204 S8000
G1 X137.733 Y114.742 E.25413
G1 X137.733 Y115.234 E.01915
G1 X144.267 Y115.234 E.25413
G1 X144.267 Y114.802 E.01682
; WIPE_START
G1 X144.267 Y115.234 E-.16431
G1 X143.699 Y115.234 E-.21569
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I.547 J1.087 P1  F60000
G1 X146.422 Y113.864 Z2.6
G1 Z2.2
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X147.893 Y115.336 E.0669
G1 X147.786 Y115.336 E.00345
G1 X148.167 Y113.864 E.04886
G1 X149.638 Y115.336 E.0669
G1 X149.063 Y115.336 E.01848
G1 X149.457 Y113.864 E.04897
G1 X149.911 Y113.864 E.0146
G1 X151.284 Y115.237 E.0624
G1 X151.284 Y115.32 E.00269
G1 X150.34 Y115.336 E.03033
G1 X150.734 Y113.864 E.04897
; WIPE_START
G1 X150.476 Y114.83 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I.059 J-1.216 P1  F60000
G1 X139.33 Y114.292 Z2.6
G1 Z2.2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X139.872 Y114.292 E.01743
G1 X139.444 Y113.864 E.01945
G1 X139.241 Y113.864 E.00654
G1 X139.126 Y114.292 E.01424
G1 X138.331 Y114.292 E.02558
M204 S10000
G1 X139.037 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X137.964 Y113.864 E.03452
G1 X137.849 Y114.292 E.01424
G1 X138.127 Y114.292 E.00894
G1 X137.652 Y113.864 E.02056
G1 X132.193 Y115.336 E.18181
G1 X130.721 Y113.864 E.0669
G1 X130.301 Y113.864 E.01352
G1 X129.907 Y115.336 E.04897
G1 X130.448 Y115.336 E.0174
G1 X128.977 Y113.864 E.0669
G1 X129.024 Y113.864 E.00151
G1 X128.63 Y115.336 E.04897
; WIPE_START
G1 X128.889 Y114.37 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I-.93 J.785 P1  F60000
G1 X129.703 Y115.336 Z2.6
G1 Z2.2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X128.703 Y115.336 E.03215
G1 X127.232 Y113.864 E.0669
; WIPE_START
G1 X127.94 Y114.572 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I.365 J-1.161 P1  F60000
G1 X125.691 Y113.864 Z2.6
G1 Z2.2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X126.47 Y113.864 E.02503
G1 X126.076 Y115.336 E.04897
G1 X126.959 Y115.336 E.0284
G1 X125.488 Y113.864 E.0669
M73 P64 R5
G1 X125.193 Y113.864 E.00949
G1 X124.799 Y115.336 E.04897
G1 X125.214 Y115.336 E.01337
G1 X123.743 Y113.864 E.0669
G1 X123.916 Y113.864 E.00554
G1 X123.522 Y115.336 E.04897
M204 S10000
G1 X123.47 Y115.336 F60000
G1 F13265.217
M204 S8000
G1 X121.999 Y113.864 E.0669
G1 X121.362 Y113.864 E.02049
G1 X120.967 Y115.336 E.04897
G1 X121.725 Y115.336 E.02438
G1 X120.635 Y114.245 E.04959
G1 X120.635 Y114.593 E.01119
G1 X123.353 Y113.864 E.0905
G1 X122.957 Y113.864 E.01275
M204 S10000
G1 X122.639 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X122.244 Y115.336 E.04897
G1 X122.629 Y115.336 E.01238
G1 X128.12 Y113.864 E.18277
G1 X127.747 Y113.864 E.01198
G1 X127.353 Y115.336 E.04897
G1 X127.396 Y115.336 E.00138
G1 X132.886 Y113.864 E.18277
G1 X132.461 Y115.336 E.04924
G1 X132.396 Y115.336 E.00209
M204 S10000
G1 X131.958 Y115.336 F60000
G1 F13265.217
M204 S8000
G1 X131.184 Y115.336 E.02489
G1 X131.578 Y113.864 E.04897
G1 X130.925 Y113.864 E.021
; WIPE_START
G1 X131.578 Y113.864 E-.24821
G1 X131.488 Y114.199 E-.13179
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I.395 J1.151 P1  F60000
G1 X132.466 Y113.864 Z2.6
G1 Z2.2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X133.937 Y115.336 E.0669
G1 X133.738 Y115.336 E.0064
G1 X134.132 Y113.864 E.04897
G1 X134.211 Y113.864 E.00251
G1 X135.682 Y115.336 E.0669
G1 X136.292 Y115.336 E.01964
G1 X136.687 Y113.864 E.04897
; WIPE_START
G1 X136.428 Y114.83 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I-1.206 J.163 P1  F60000
G1 X136.496 Y115.336 Z2.6
G1 Z2.2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G2 X137.284 Y115.24 I.216 J-1.517 E.02581
G1 X135.955 Y113.864 E.0615
G1 X135.409 Y113.864 E.01754
G1 X135.015 Y115.336 E.04897
G1 X134.141 Y115.336 E.02813
; WIPE_START
G1 X135.015 Y115.336 E-.33237
G1 X135.048 Y115.214 E-.04763
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I-1.151 J.394 P1  F60000
G1 X155.626 Y175.3 Z2.6
G1 Z2.2
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.43172
G1 F13888.888
M204 S8000
G1 X156.467 Y175.3 E.02584
; COOLING_NODE: 0
; WIPE_START
G1 X155.626 Y175.3 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I1.011 J-.677 P1  F60000
G1 X115.713 Y115.684 Z2.6
G1 Z2.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X112.416 Y115.684 E.10603
G1 X112.416 Y113.516 E.0697
G1 X115.713 Y113.516 E.10603
G1 X115.713 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X116.12 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X112.009 Y116.091 E.13221
G1 X112.009 Y113.109 E.09588
G1 X116.12 Y113.109 E.13221
G1 X116.12 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X116.528 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X111.602 Y116.498 E.15839
G1 X111.602 Y112.702 E.12206
G1 X116.528 Y112.702 E.15839
G1 X116.528 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X116.632 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F2945
M204 S5000
G1 X111.21 Y116.89 E.1615
G1 X111.21 Y112.31 E.13642
G1 X111.432 Y112.31 E.00661
G1 X111.832 Y112.31 E.01191
G1 X112.232 Y112.31 E.01191
G1 X112.632 Y112.31 E.01191
G1 X113.032 Y112.31 E.01191
G1 X113.432 Y112.31 E.01191
G1 X113.832 Y112.31 E.01191
G1 X114.232 Y112.31 E.01191
G1 X114.632 Y112.31 E.01191
G1 X115.032 Y112.31 E.01191
G1 F2887.816
G1 X115.432 Y112.31 E.01191
G1 F2260.206
G1 X115.832 Y112.31 E.01191
G1 F1709.397
G1 X116.232 Y112.31 E.01191
G1 F1235.388
G1 X116.632 Y112.31 E.01191
G1 F838.178
G1 X116.92 Y112.31 E.00857
M106 S51
M106 S127.5
G1 F600
G1 X116.92 Y116.89 E.13642
M106 S51
M106 S127.5
G1 F785.221
G1 X116.692 Y116.89 E.00678
M106 S51
; WIPE_START
M204 S8000
G1 X115.692 Y116.89 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.6 I1.186 J-.275 P1  F60000
G1 X115.321 Y115.292 Z2.6
G1 Z2.2
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X115.321 Y113.908 E.04121
G1 X112.808 Y113.908 E.07486
G1 X112.808 Y115.292 E.04121
G1 X115.261 Y115.292 E.07307
M204 S10000
G1 X114.881 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X114.881 Y114.348 E.02
G1 X113.248 Y114.348 E.0649
G1 X113.248 Y114.852 E.02
G1 X114.821 Y114.852 E.06252
; CHANGE_LAYER
; Z_HEIGHT: 2.4
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F10731.32
G1 X113.821 Y114.852 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 12/27
; update layer progress
M73 L12
M991 S0 P11 ;notify layer change
M106 S61.2
; OBJECT_ID: 16
; COOLING_NODE: 0
; start printing object, unique label id: 16
M624 BAAAAAAAAAA=
M204 S10000
G17
G3 Z2.6 I-.749 J.959 P1  F60000
G1 X195.144 Y178.407 Z2.6
G1 Z2.4
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X194.745 Y178.406 E.01283
G3 X194.575 Y171.609 I.255 J-3.407 E.32325
G1 X194.915 Y171.583 E.01097
G3 X195.255 Y178.406 I.085 J3.416 E.33969
G1 X195.204 Y178.407 E.00166
; COOLING_NODE: 0
M204 S10000
G1 X195.142 Y178.001 F60000
G1 F13265.217
M204 S8000
G1 X194.775 Y178 E.0118
G3 X194.625 Y172.013 I.225 J-3.001 E.28471
G1 X194.925 Y171.991 E.00966
G3 X195.225 Y178 I.075 J3.009 E.2992
G1 X195.202 Y178 E.00073
; COOLING_NODE: 0
M204 S10000
G1 X195.141 Y177.595 F60000
G1 F13265.217
M204 S8000
G1 X194.806 Y177.594 E.01079
G3 X194.676 Y172.417 I.194 J-2.595 E.24618
G1 X194.935 Y172.398 E.00835
G3 X195.201 Y177.594 I.065 J2.601 E.25848
; COOLING_NODE: 0
M204 S250
G1 X195.141 Y177.204 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X194.835 Y177.203 E.0091
G3 X194.725 Y172.807 I.165 J-2.204 E.19366
G1 X194.945 Y172.79 E.00657
G3 X195.2 Y177.2 I.055 J2.209 E.20245
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X194.835 Y177.203 E-.13887
G1 X194.401 Y177.128 E-.16723
G1 X194.22 Y177.057 E-.0739
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I-1.085 J.55 P1  F60000
G1 X201.584 Y191.584 Z2.8
G1 Z2.4
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y191.584 E.42342
G1 X188.416 Y170.416 E.68067
G1 X201.584 Y170.416 E.42342
G1 X201.584 Y191.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y191.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y191.991 E.4496
G1 X188.009 Y170.009 E.70685
G1 X201.991 Y170.009 E.4496
G1 X201.991 Y191.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y192.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y192.398 E.47578
G1 X187.602 Y169.602 E.73303
G1 X202.398 Y169.602 E.47578
G1 X202.398 Y192.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y192.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y192.79 E.46408
G1 X187.21 Y169.21 E.70237
G1 X202.79 Y169.21 E.46408
G1 X202.79 Y192.73 E.70058
; object ids of layer 12 start: 8,12,16
M624 BwAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer12 end: 8,12,16
M625
; WIPE_START
M204 S8000
G1 X201.79 Y192.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I.921 J-.796 P1  F60000
G1 X200.654 Y191.42 Z2.8
G1 Z2.4
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42179
G1 F14252.909
M204 S8000
G1 X201.251 Y190.824 E.02524
G1 X201.251 Y190.288 E.01604
G1 X200.288 Y191.251 E.04074
G1 X199.752 Y191.251 E.01604
G1 X201.251 Y189.752 E.06342
G1 X201.251 Y189.216 E.01604
G1 X199.216 Y191.251 E.08609
G1 X198.681 Y191.251 E.01604
G1 X201.251 Y188.681 E.10877
G1 X201.251 Y188.145 E.01604
G1 X198.145 Y191.251 E.13145
G1 X197.609 Y191.251 E.01604
G1 X201.251 Y187.609 E.15413
G1 X201.251 Y187.073 E.01604
G1 X197.073 Y191.251 E.1768
G1 X196.537 Y191.251 E.01604
G1 X201.251 Y186.537 E.19948
G1 X201.251 Y186.002 E.01604
G1 X196.002 Y191.251 E.22216
G1 X195.466 Y191.251 E.01604
G1 X201.251 Y185.466 E.24484
G1 X201.251 Y184.93 E.01604
G1 X194.93 Y191.251 E.26751
G1 X194.394 Y191.251 E.01604
G1 X201.251 Y184.394 E.29019
G1 X201.251 Y183.858 E.01604
G1 X193.858 Y191.251 E.31287
G1 X193.323 Y191.251 E.01604
G1 X201.251 Y183.323 E.33555
G1 X201.251 Y182.787 E.01604
G1 X192.787 Y191.251 E.35823
G1 X192.251 Y191.251 E.01604
G1 X201.251 Y182.251 E.3809
G1 X201.251 Y181.715 E.01604
G1 X191.715 Y191.251 E.40358
G1 X191.179 Y191.251 E.01604
G1 X201.251 Y181.179 E.42626
G1 X201.251 Y180.644 E.01604
G1 X190.644 Y191.251 E.44894
G1 X190.108 Y191.251 E.01604
G1 X201.251 Y180.108 E.47161
G1 X201.251 Y179.572 E.01604
G1 X189.572 Y191.251 E.49429
G1 X189.036 Y191.251 E.01604
G1 X201.251 Y179.036 E.51697
G1 X201.251 Y178.5 E.01604
G1 X188.749 Y191.001 E.5291
G1 X188.749 Y190.466 E.01604
G1 X201.251 Y177.965 E.5291
G1 X201.251 Y177.429 E.01604
G1 X188.749 Y189.93 E.5291
G1 X188.749 Y189.394 E.01604
G1 X201.251 Y176.893 E.5291
G1 X201.251 Y176.357 E.01604
G1 X188.749 Y188.858 E.5291
G1 X188.749 Y188.322 E.01604
G1 X201.251 Y175.821 E.5291
G1 X201.251 Y175.286 E.01604
G1 X188.749 Y187.787 E.5291
G1 X188.749 Y187.251 E.01604
G1 X201.251 Y174.75 E.5291
M73 P65 R5
G1 X201.251 Y174.214 E.01604
G1 X188.749 Y186.715 E.5291
G1 X188.749 Y186.179 E.01604
G1 X196.49 Y178.438 E.32762
G3 X195.714 Y178.679 I-1.518 J-3.529 E.02436
G1 X188.749 Y185.643 E.29477
G1 X188.749 Y185.108 E.01604
G1 X195.11 Y178.748 E.26919
G3 X194.596 Y178.726 I-.066 J-4.499 E.0154
G1 X188.749 Y184.572 E.24744
G1 X188.749 Y184.036 E.01604
G1 X194.139 Y178.647 E.2281
G3 X193.725 Y178.525 I.404 J-2.127 E.01293
G1 X188.749 Y183.5 E.21059
G1 X188.749 Y182.964 E.01604
G1 X193.348 Y178.366 E.19465
G3 X193.004 Y178.174 I.786 J-1.821 E.01181
G1 X188.749 Y182.429 E.18007
G1 X188.749 Y181.893 E.01604
G1 X192.689 Y177.953 E.16674
G3 X192.402 Y177.705 I1.103 J-1.564 E.01139
G1 X188.749 Y181.357 E.15459
G1 X188.749 Y180.821 E.01604
G1 X192.143 Y177.427 E.14364
G3 X191.909 Y177.125 I1.387 J-1.316 E.01145
G1 X188.749 Y180.285 E.13374
G1 X188.749 Y179.75 E.01604
G1 X191.705 Y176.794 E.1251
G3 X191.533 Y176.43 I1.731 J-1.041 E.01206
G1 X188.749 Y179.214 E.11782
G1 X188.749 Y178.678 E.01604
G1 X191.396 Y176.031 E.11202
G3 X191.3 Y175.592 I2.15 J-.701 E.01349
G1 X188.749 Y178.142 E.10795
G1 X188.749 Y177.606 E.01604
G1 X191.253 Y175.102 E.10598
G3 X191.28 Y174.54 I4.2 J-.083 E.01686
G1 X188.749 Y177.071 E.10711
G1 X188.749 Y176.535 E.01604
G1 X191.722 Y173.563 E.1258
; WIPE_START
G1 X191.015 Y174.27 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I1.109 J-.501 P1  F60000
G1 X189.346 Y170.58 Z2.8
G1 Z2.4
G1 E.4 F1800
G1 F14252.909
M204 S8000
G1 X188.749 Y171.177 E.02527
G1 X188.749 Y171.713 E.01604
G1 X189.713 Y170.749 E.04076
G1 X190.248 Y170.749 E.01604
G1 X188.749 Y172.248 E.06344
G1 X188.749 Y172.784 E.01604
G1 X190.784 Y170.749 E.08612
G1 X191.32 Y170.749 E.01604
G1 X188.749 Y173.32 E.10879
G1 X188.749 Y173.856 E.01604
G1 X191.856 Y170.749 E.13147
G1 X192.392 Y170.749 E.01604
G1 X188.749 Y174.392 E.15415
G1 X188.749 Y174.927 E.01604
G1 X192.927 Y170.749 E.17683
G1 X193.463 Y170.749 E.01604
G1 X188.749 Y175.463 E.19951
G1 X188.749 Y175.999 E.01604
G1 X193.999 Y170.749 E.22218
G1 X194.535 Y170.749 E.01604
G1 X193.854 Y171.43 E.0288
G3 X194.543 Y171.277 I1.464 J4.962 E.02114
G1 X195.071 Y170.749 E.02232
G1 X195.606 Y170.749 E.01604
G1 X195.101 Y171.254 E.02137
G3 X195.594 Y171.298 I.028 J2.481 E.01481
G1 X196.142 Y170.749 E.02322
G1 X196.678 Y170.749 E.01604
G1 X196.033 Y171.394 E.02729
G3 X196.429 Y171.534 I-.5 J2.047 E.01259
G1 X197.214 Y170.749 E.03321
G1 X197.75 Y170.749 E.01604
G1 X196.791 Y171.708 E.04055
G3 X197.123 Y171.912 I-.853 J1.759 E.01168
G1 X198.285 Y170.749 E.04919
G1 X198.821 Y170.749 E.01604
G1 X197.427 Y172.144 E.05903
G3 X197.703 Y172.404 I-1.16 J1.509 E.01136
G1 X199.357 Y170.749 E.07002
G1 X199.893 Y170.749 E.01604
G1 X197.951 Y172.691 E.08217
G3 X198.171 Y173.007 I-1.47 J1.256 E.01154
G1 X200.429 Y170.749 E.09555
G1 X200.964 Y170.749 E.01604
G1 X198.364 Y173.35 E.11006
G3 X198.524 Y173.726 I-1.798 J.985 E.01225
G1 X201.251 Y170.999 E.11541
G1 X201.251 Y171.535 E.01604
G1 X198.647 Y174.138 E.11019
G3 X198.728 Y174.593 I-2.235 J.632 E.01385
G1 X201.251 Y172.071 E.10677
G1 X201.251 Y172.607 E.01604
G1 X198.746 Y175.111 E.106
G3 X198.682 Y175.711 I-3.031 J-.02 E.01808
G1 X201.251 Y173.142 E.10871
G1 X201.251 Y173.678 E.01604
G1 X198.016 Y176.913 E.1369
; OBJECT_ID: 12
; COOLING_NODE: 0
; WIPE_START
G1 X198.723 Y176.206 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 16
M625
; start printing object, unique label id: 12
M624 AgAAAAAAAAA=
M204 S10000
G17
G3 Z2.8 I1.217 J-.024 P1  F60000
G1 X197.558 Y117.257 Z2.8
G1 Z2.4
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X197.508 Y117.327 E.00277
G3 X194.593 Y111.607 I-2.499 J-2.329 E.42183
G1 X194.915 Y111.583 E.01039
G3 X197.859 Y116.881 I.094 J3.415 E.23972
G1 X197.596 Y117.21 E.01355
; COOLING_NODE: 0
M204 S10000
G1 X197.165 Y117.088 F60000
G1 F13265.217
M204 S8000
G1 X196.993 Y117.258 E.00779
G3 X194.638 Y112.012 I-1.987 J-2.26 E.3619
G1 X194.925 Y111.991 E.00924
G3 X197.21 Y117.048 I.081 J3.008 E.2271
; COOLING_NODE: 0
M204 S10000
G1 X196.881 Y116.797 F60000
G1 F13265.217
M204 S8000
G1 X196.723 Y116.952 E.00713
G3 X194.684 Y112.417 I-1.719 J-1.953 E.31288
G1 X194.935 Y112.398 E.0081
G3 X196.924 Y116.754 I.069 J2.601 E.19559
; COOLING_NODE: 0
M204 S250
G1 X196.607 Y116.515 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X196.285 Y116.787 E.01255
G3 X194.728 Y112.807 I-1.284 J-1.792 E.23897
G1 X194.945 Y112.79 E.00648
G3 X196.642 Y116.467 I.056 J2.204 E.15288
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X196.285 Y116.787 E-.182
G1 X195.909 Y117.015 E-.16696
G1 X195.832 Y117.041 E-.03105
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I-1.132 J.448 P1  F60000
G1 X201.584 Y131.584 Z2.8
G1 Z2.4
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y131.584 E.42342
G1 X188.416 Y110.416 E.68067
G1 X201.584 Y110.416 E.42342
G1 X201.584 Y131.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y131.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y131.991 E.4496
G1 X188.009 Y110.009 E.70685
G1 X201.991 Y110.009 E.4496
G1 X201.991 Y131.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y132.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y132.398 E.47578
G1 X187.602 Y109.602 E.73303
G1 X202.398 Y109.602 E.47578
G1 X202.398 Y132.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y132.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y132.79 E.46408
G1 X187.21 Y109.21 E.70237
G1 X202.79 Y109.21 E.46408
G1 X202.79 Y132.73 E.70058
; WIPE_START
M204 S8000
G1 X201.79 Y132.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I.921 J-.796 P1  F60000
G1 X200.654 Y131.42 Z2.8
G1 Z2.4
G1 E.4 F1800
M106 S127.5
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42179
G1 F14252.909
M204 S8000
G1 X201.251 Y130.824 E.02524
G1 X201.251 Y130.288 E.01604
G1 X200.288 Y131.251 E.04074
G1 X199.752 Y131.251 E.01604
G1 X201.251 Y129.752 E.06342
G1 X201.251 Y129.216 E.01604
G1 X199.216 Y131.251 E.08609
G1 X198.681 Y131.251 E.01604
G1 X201.251 Y128.681 E.10877
G1 X201.251 Y128.145 E.01604
G1 X198.145 Y131.251 E.13145
G1 X197.609 Y131.251 E.01604
G1 X201.251 Y127.609 E.15413
G1 X201.251 Y127.073 E.01604
G1 X197.073 Y131.251 E.1768
G1 X196.537 Y131.251 E.01604
G1 X201.251 Y126.537 E.19948
G1 X201.251 Y126.002 E.01604
G1 X196.002 Y131.251 E.22216
G1 X195.466 Y131.251 E.01604
G1 X201.251 Y125.466 E.24484
G1 X201.251 Y124.93 E.01604
G1 X194.93 Y131.251 E.26751
G1 X194.394 Y131.251 E.01604
G1 X201.251 Y124.394 E.29019
G1 X201.251 Y123.858 E.01604
G1 X193.858 Y131.251 E.31287
G1 X193.323 Y131.251 E.01604
G1 X201.251 Y123.323 E.33555
G1 X201.251 Y122.787 E.01604
G1 X192.787 Y131.251 E.35823
G1 X192.251 Y131.251 E.01604
G1 X201.251 Y122.251 E.3809
G1 X201.251 Y121.715 E.01604
G1 X191.715 Y131.251 E.40358
G1 X191.179 Y131.251 E.01604
G1 X201.251 Y121.179 E.42626
G1 X201.251 Y120.644 E.01604
G1 X190.644 Y131.251 E.44894
G1 X190.108 Y131.251 E.01604
G1 X201.251 Y120.108 E.47161
G1 X201.251 Y119.572 E.01604
G1 X189.572 Y131.251 E.49429
G1 X189.036 Y131.251 E.01604
G1 X201.251 Y119.036 E.51697
G1 X201.251 Y118.5 E.01604
G1 X188.749 Y131.001 E.5291
G1 X188.749 Y130.466 E.01604
G1 X201.251 Y117.965 E.5291
G1 X201.251 Y117.429 E.01604
G1 X188.749 Y129.93 E.5291
G1 X188.749 Y129.394 E.01604
G1 X201.251 Y116.893 E.5291
G1 X201.251 Y116.357 E.01604
G1 X188.749 Y128.858 E.5291
G1 X188.749 Y128.322 E.01604
G1 X201.251 Y115.821 E.5291
G1 X201.251 Y115.286 E.01604
G1 X188.749 Y127.787 E.5291
G1 X188.749 Y127.251 E.01604
G1 X201.251 Y114.75 E.5291
G1 X201.251 Y114.214 E.01604
G1 X188.749 Y126.715 E.5291
G1 X188.749 Y126.179 E.01604
G1 X196.487 Y118.442 E.32749
G3 X195.714 Y118.679 I-1.544 J-3.653 E.02424
G1 X188.749 Y125.643 E.29477
G1 X188.749 Y125.108 E.01604
G1 X195.108 Y118.749 E.26911
G3 X194.596 Y118.726 I-.003 J-5.452 E.01535
G1 X188.749 Y124.572 E.24744
M73 P66 R5
G1 X188.749 Y124.036 E.01604
G1 X194.139 Y118.647 E.2281
G3 X193.725 Y118.524 I.404 J-2.126 E.01293
G1 X188.749 Y123.5 E.21059
G1 X188.749 Y122.964 E.01604
G1 X193.348 Y118.366 E.19465
G3 X193.004 Y118.174 I.784 J-1.817 E.01181
G1 X188.749 Y122.429 E.18007
G1 X188.749 Y121.893 E.01604
G1 X192.689 Y117.953 E.16674
G3 X192.402 Y117.705 I1.097 J-1.555 E.01139
G1 X188.749 Y121.357 E.15459
G1 X188.749 Y120.821 E.01604
G1 X192.142 Y117.429 E.14359
G3 X191.909 Y117.125 I1.398 J-1.313 E.01146
G1 X188.749 Y120.285 E.13374
G1 X188.749 Y119.75 E.01604
G1 X191.705 Y116.794 E.1251
G3 X191.533 Y116.43 I1.736 J-1.043 E.01206
G1 X188.749 Y119.214 E.11782
G1 X188.749 Y118.678 E.01604
G1 X191.396 Y116.031 E.11202
G3 X191.3 Y115.592 I2.149 J-.7 E.01349
G1 X188.749 Y118.142 E.10795
G1 X188.749 Y117.606 E.01604
G1 X191.253 Y115.102 E.10598
G3 X191.28 Y114.54 I4.194 J-.084 E.01686
G1 X188.749 Y117.071 E.10711
G1 X188.749 Y116.535 E.01604
G1 X191.722 Y113.563 E.1258
; WIPE_START
G1 X191.015 Y114.27 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I1.109 J-.501 P1  F60000
G1 X189.346 Y110.58 Z2.8
G1 Z2.4
G1 E.4 F1800
G1 F14252.909
M204 S8000
G1 X188.749 Y111.177 E.02527
G1 X188.749 Y111.713 E.01604
G1 X189.713 Y110.749 E.04076
G1 X190.248 Y110.749 E.01604
G1 X188.749 Y112.248 E.06344
G1 X188.749 Y112.784 E.01604
G1 X190.784 Y110.749 E.08612
G1 X191.32 Y110.749 E.01604
G1 X188.749 Y113.32 E.10879
G1 X188.749 Y113.856 E.01604
G1 X191.856 Y110.749 E.13147
G1 X192.392 Y110.749 E.01604
G1 X188.749 Y114.392 E.15415
G1 X188.749 Y114.927 E.01604
G1 X192.927 Y110.749 E.17683
G1 X193.463 Y110.749 E.01604
G1 X188.749 Y115.463 E.19951
G1 X188.749 Y115.999 E.01604
G1 X193.999 Y110.749 E.22218
G1 X194.535 Y110.749 E.01604
G1 X193.854 Y111.43 E.0288
G3 X194.542 Y111.278 I1.102 J3.354 E.02112
G1 X195.071 Y110.749 E.02236
G1 X195.606 Y110.749 E.01604
G1 X195.101 Y111.254 E.02137
G3 X195.594 Y111.298 I.028 J2.48 E.01481
G1 X196.142 Y110.749 E.02322
G1 X196.678 Y110.749 E.01604
G1 X196.033 Y111.394 E.02729
G3 X196.429 Y111.534 I-.5 J2.048 E.01259
G1 X197.214 Y110.749 E.03321
G1 X197.75 Y110.749 E.01604
G1 X196.791 Y111.708 E.04055
G3 X197.123 Y111.912 I-.852 J1.758 E.01168
G1 X198.285 Y110.749 E.04919
G1 X198.821 Y110.749 E.01604
G1 X197.427 Y112.144 E.05903
G3 X197.703 Y112.404 I-1.161 J1.51 E.01136
G1 X199.357 Y110.749 E.07002
G1 X199.893 Y110.749 E.01604
G1 X197.951 Y112.691 E.08217
G3 X198.172 Y113.006 I-1.466 J1.264 E.01153
G1 X200.429 Y110.749 E.09549
G1 X200.964 Y110.749 E.01604
G1 X198.364 Y113.35 E.11006
G3 X198.524 Y113.726 I-1.796 J.984 E.01225
G1 X201.251 Y110.999 E.11541
G1 X201.251 Y111.535 E.01604
G1 X198.647 Y114.138 E.11019
G3 X198.728 Y114.593 I-2.235 J.632 E.01385
G1 X201.251 Y112.071 E.10677
G1 X201.251 Y112.607 E.01604
G1 X198.746 Y115.111 E.106
G3 X198.682 Y115.711 I-3.031 J-.02 E.01808
G1 X201.251 Y113.142 E.10871
G1 X201.251 Y113.678 E.01604
G1 X198.016 Y116.913 E.1369
; OBJECT_ID: 8
; COOLING_NODE: 0
; WIPE_START
G1 X198.723 Y116.206 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 12
M106 S61.2
M625
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M106 S127.5
M204 S10000
G17
G3 Z2.8 I.011 J-1.217 P1  F60000
G1 X140.719 Y115.684 Z2.8
G1 Z2.4
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X123.853 Y115.684 E.54237
G1 X123.453 Y115.684 E.01286
G1 F12230.35
G1 X123.053 Y115.684 E.01286
G1 F10898.137
G1 X122.653 Y115.684 E.01286
G1 F9642.723
G1 X122.253 Y115.684 E.01286
G1 F8464.109
G1 X121.853 Y115.684 E.01286
G1 F7362.296
G1 X121.453 Y115.684 E.01286
G1 F6337.282
G1 X121.053 Y115.684 E.01286
G1 F5389.068
G1 X120.653 Y115.684 E.01286
G1 F4517.655
G1 X120.253 Y115.684 E.01286
G1 F3723.041
G1 X119.853 Y115.684 E.01286
G1 F3005.227
G1 X119.453 Y115.684 E.01286
G1 F2364.214
G1 X119.053 Y115.684 E.01286
G1 F1800
G1 X118.67 Y115.684 E.0123
M106 S61.2
M106 S127.5
; FEATURE: Overhang wall
G1 F3000
M204 S5000
G1 X117.33 Y115.684 E.04311
M106 S61.2
M106 S127.5
; FEATURE: Inner wall
G1 F1800
M204 S8000
G1 X116.947 Y115.684 E.0123
M106 S61.2
M106 S127.5
G1 F2364.214
G1 X116.547 Y115.684 E.01286
G1 F3005.227
G1 X116.147 Y115.684 E.01286
G1 F3723.041
G1 X115.747 Y115.684 E.01286
G1 F4517.655
G1 X115.347 Y115.684 E.01286
G1 F5389.068
G1 X114.947 Y115.684 E.01286
G1 F6337.282
G1 X114.547 Y115.684 E.01286
G1 F7362.296
G1 X114.147 Y115.684 E.01286
G1 F8464.109
G1 X113.747 Y115.684 E.01286
G1 F9642.723
G1 X113.347 Y115.684 E.01286
G1 F10898.137
G1 X112.947 Y115.684 E.01286
G1 F12683.135
G1 X112.416 Y115.684 E.01707
G1 F13265.217
G1 X112.416 Y115.284 E.01286
G1 X112.416 Y113.916 E.04398
G1 X112.416 Y113.516 E.01286
G1 F12683.135
G1 X112.947 Y113.516 E.01707
G1 F10898.137
G1 X113.347 Y113.516 E.01286
G1 F9642.723
G1 X113.747 Y113.516 E.01286
G1 F8464.109
G1 X114.147 Y113.516 E.01286
G1 F7362.296
G1 X114.547 Y113.516 E.01286
G1 F6337.282
G1 X114.947 Y113.516 E.01286
G1 F5389.068
G1 X115.347 Y113.516 E.01286
G1 F4517.655
G1 X115.747 Y113.516 E.01286
G1 F3723.041
G1 X116.147 Y113.516 E.01286
G1 F3005.227
G1 X116.547 Y113.516 E.01286
G1 F2364.214
G1 X116.947 Y113.516 E.01286
G1 F1800
G1 X117.33 Y113.516 E.0123
M106 S61.2
M106 S127.5
; FEATURE: Overhang wall
G1 F3000
M204 S5000
G1 X118.67 Y113.516 E.04311
M106 S61.2
M106 S127.5
; FEATURE: Inner wall
G1 F1800
M204 S8000
G1 X119.053 Y113.516 E.0123
M106 S61.2
M106 S127.5
G1 F2364.214
G1 X119.453 Y113.516 E.01286
G1 F3005.227
G1 X119.853 Y113.516 E.01286
G1 F3723.041
G1 X120.253 Y113.516 E.01286
G1 F4517.655
G1 X120.653 Y113.516 E.01286
G1 F5389.068
G1 X121.053 Y113.516 E.01286
G1 F6337.282
G1 X121.453 Y113.516 E.01286
G1 F7362.296
G1 X121.853 Y113.516 E.01286
G1 F8464.109
G1 X122.253 Y113.516 E.01286
G1 F9642.723
G1 X122.653 Y113.516 E.01286
G1 F10898.137
G1 X123.053 Y113.516 E.01286
G1 F12230.35
G1 X123.453 Y113.516 E.01286
G1 F13265.217
G1 X123.853 Y113.516 E.01286
G1 X157.584 Y113.516 E1.08466
G1 X157.584 Y115.684 E.0697
G1 X140.779 Y115.684 E.54037
; COOLING_NODE: 0
M204 S10000
G1 X141.126 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X141.126 Y175.291 E1.90366
G1 X140.874 Y175.291 E.00813
G1 X140.874 Y116.091 E1.90366
G1 X123.853 Y116.091 E.54732
G1 X123.453 Y116.091 E.01286
G1 F12230.35
G1 X123.053 Y116.091 E.01286
G1 F10898.137
G1 X122.653 Y116.091 E.01286
G1 F9642.723
G1 X122.253 Y116.091 E.01286
G1 F8464.109
G1 X121.853 Y116.091 E.01286
G1 F7362.296
G1 X121.453 Y116.091 E.01286
G1 F6337.282
G1 X121.053 Y116.091 E.01286
G1 F5389.068
G1 X120.653 Y116.091 E.01286
G1 F4517.655
G1 X120.253 Y116.091 E.01286
G1 F3723.041
G1 X119.853 Y116.091 E.01286
G1 F3005.227
G1 X119.453 Y116.091 E.01286
G1 F2364.214
G1 X119.053 Y116.091 E.01286
G1 F1800
G1 X118.67 Y116.091 E.0123
M106 S61.2
M106 S127.5
; FEATURE: Overhang wall
G1 F3000
M204 S5000
G1 X117.33 Y116.091 E.04311
M106 S61.2
M106 S127.5
; FEATURE: Inner wall
G1 F1800
M204 S8000
G1 X116.947 Y116.091 E.0123
M106 S61.2
M106 S127.5
G1 F2364.214
G1 X116.547 Y116.091 E.01286
G1 F3005.227
G1 X116.147 Y116.091 E.01286
G1 F3723.041
G1 X115.747 Y116.091 E.01286
G1 F4517.655
G1 X115.347 Y116.091 E.01286
G1 F5389.068
G1 X114.947 Y116.091 E.01286
G1 F6337.282
G1 X114.547 Y116.091 E.01286
G1 F7362.296
G1 X114.147 Y116.091 E.01286
G1 F8464.109
G1 X113.747 Y116.091 E.01286
G1 F9642.723
G1 X113.347 Y116.091 E.01286
G1 F10898.137
G1 X112.947 Y116.091 E.01286
G1 F12230.35
G1 X112.547 Y116.091 E.01286
G1 F13265.217
G1 X112.009 Y116.091 E.0173
G1 X112.009 Y113.109 E.09588
G1 X112.547 Y113.109 E.0173
G1 F12230.35
G1 X112.947 Y113.109 E.01286
G1 F10898.137
G1 X113.347 Y113.109 E.01286
G1 F9642.723
G1 X113.747 Y113.109 E.01286
G1 F8464.109
G1 X114.147 Y113.109 E.01286
G1 F7362.296
G1 X114.547 Y113.109 E.01286
G1 F6337.282
G1 X114.947 Y113.109 E.01286
G1 F5389.068
G1 X115.347 Y113.109 E.01286
G1 F4517.655
G1 X115.747 Y113.109 E.01286
G1 F3723.041
G1 X116.147 Y113.109 E.01286
G1 F3005.227
G1 X116.547 Y113.109 E.01286
G1 F2364.214
G1 X116.947 Y113.109 E.01286
G1 F1800
G1 X117.33 Y113.109 E.0123
M106 S61.2
M106 S127.5
; FEATURE: Overhang wall
G1 F3000
M204 S5000
G1 X118.67 Y113.109 E.04311
M106 S61.2
M106 S127.5
; FEATURE: Inner wall
G1 F1800
M204 S8000
G1 X119.053 Y113.109 E.0123
M106 S61.2
M106 S127.5
G1 F2364.214
G1 X119.453 Y113.109 E.01286
G1 F3005.227
G1 X119.853 Y113.109 E.01286
G1 F3723.041
G1 X120.253 Y113.109 E.01286
G1 F4517.655
G1 X120.653 Y113.109 E.01286
G1 F5389.068
G1 X121.053 Y113.109 E.01286
G1 F6337.282
G1 X121.453 Y113.109 E.01286
G1 F7362.296
G1 X121.853 Y113.109 E.01286
G1 F8464.109
G1 X122.253 Y113.109 E.01286
G1 F9642.723
G1 X122.653 Y113.109 E.01286
G1 F10898.137
G1 X123.053 Y113.109 E.01286
G1 F12230.35
G1 X123.453 Y113.109 E.01286
G1 F13265.217
G1 X123.853 Y113.109 E.01286
G1 X157.991 Y113.109 E1.09775
G1 X157.991 Y116.091 E.09588
G1 X155.126 Y116.091 E.09211
G1 X155.126 Y175.291 E1.90366
G1 X154.874 Y175.291 E.00813
G1 X154.874 Y116.091 E1.90366
G1 X141.186 Y116.091 E.44013
; COOLING_NODE: 0
M204 S10000
G1 X141.534 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X141.534 Y174.902 E1.87806
G1 X142.497 Y174.902 E.03098
G1 X142.497 Y175.698 E.02559
G1 X139.503 Y175.698 E.09627
G1 X139.503 Y174.902 E.02559
G1 X140.466 Y174.902 E.03098
G1 X140.466 Y116.498 E1.87806
G1 X123.853 Y116.498 E.53423
G1 X123.453 Y116.498 E.01286
G1 F12230.35
G1 X123.053 Y116.498 E.01286
G1 F10898.137
G1 X122.653 Y116.498 E.01286
G1 F9642.723
G1 X122.253 Y116.498 E.01286
G1 F8464.109
G1 X121.853 Y116.498 E.01286
G1 F7362.296
G1 X121.453 Y116.498 E.01286
G1 F6337.282
G1 X121.053 Y116.498 E.01286
G1 F5389.068
G1 X120.653 Y116.498 E.01286
G1 F4517.655
G1 X120.253 Y116.498 E.01286
G1 F3723.041
G1 X119.853 Y116.498 E.01286
G1 F3005.227
G1 X119.453 Y116.498 E.01286
G1 F2364.214
G1 X119.053 Y116.498 E.01286
G1 F1800
G1 X118.67 Y116.498 E.0123
M106 S61.2
M106 S127.5
; FEATURE: Overhang wall
G1 F3000
M204 S5000
G1 X117.33 Y116.498 E.04311
M106 S61.2
M106 S127.5
; FEATURE: Inner wall
G1 F1800
M204 S8000
G1 X116.947 Y116.498 E.0123
M106 S61.2
M106 S127.5
G1 F2364.214
G1 X116.547 Y116.498 E.01286
G1 F3005.227
G1 X116.147 Y116.498 E.01286
G1 F3723.041
G1 X115.747 Y116.498 E.01286
G1 F4517.655
G1 X115.347 Y116.498 E.01286
G1 F5389.068
G1 X114.947 Y116.498 E.01286
G1 F6337.282
G1 X114.547 Y116.498 E.01286
G1 F7362.296
G1 X114.147 Y116.498 E.01286
G1 F8464.109
G1 X113.747 Y116.498 E.01286
G1 F9642.723
G1 X113.347 Y116.498 E.01286
G1 F10898.137
G1 X112.947 Y116.498 E.01286
G1 F12230.35
G1 X112.547 Y116.498 E.01286
G1 F13265.217
G1 X112.147 Y116.498 E.01286
G1 X111.602 Y116.498 E.01753
G1 X111.602 Y112.702 E.12206
G1 X112.147 Y112.702 E.01753
G1 X112.547 Y112.702 E.01286
G1 F12230.35
G1 X112.947 Y112.702 E.01286
G1 F10898.137
G1 X113.347 Y112.702 E.01286
G1 F9642.723
G1 X113.747 Y112.702 E.01286
G1 F8464.109
G1 X114.147 Y112.702 E.01286
G1 F7362.296
G1 X114.547 Y112.702 E.01286
G1 F6337.282
G1 X114.947 Y112.702 E.01286
G1 F5389.068
G1 X115.347 Y112.702 E.01286
G1 F4517.655
G1 X115.747 Y112.702 E.01286
G1 F3723.041
G1 X116.147 Y112.702 E.01286
G1 F3005.227
G1 X116.547 Y112.702 E.01286
G1 F2364.214
G1 X116.947 Y112.702 E.01286
G1 F1800
G1 X117.33 Y112.702 E.0123
M106 S61.2
M106 S127.5
; FEATURE: Overhang wall
G1 F3000
M204 S5000
G1 X118.67 Y112.702 E.04311
M106 S61.2
M106 S127.5
; FEATURE: Inner wall
G1 F1800
M204 S8000
G1 X119.053 Y112.702 E.0123
M106 S61.2
G1 F2364.214
G1 X119.453 Y112.702 E.01286
G1 F3005.227
G1 X119.853 Y112.702 E.01286
G1 F3723.041
G1 X120.253 Y112.702 E.01286
G1 F4517.655
G1 X120.653 Y112.702 E.01286
G1 F5389.068
G1 X121.053 Y112.702 E.01286
G1 F6337.282
G1 X121.453 Y112.702 E.01286
G1 F7362.296
G1 X121.853 Y112.702 E.01286
G1 F8464.109
G1 X122.253 Y112.702 E.01286
G1 F9642.723
G1 X122.653 Y112.702 E.01286
G1 F10898.137
G1 X123.053 Y112.702 E.01286
G1 F12230.35
G1 X123.453 Y112.702 E.01286
G1 F13265.217
G1 X123.853 Y112.702 E.01286
G1 X158.398 Y112.702 E1.11084
G1 X158.398 Y116.498 E.12206
G1 X155.534 Y116.498 E.09211
G1 X155.534 Y174.902 E1.87806
G1 X156.497 Y174.902 E.03098
G1 X156.497 Y175.698 E.02559
G1 X153.503 Y175.698 E.09627
G1 X153.503 Y174.902 E.02559
G1 X154.466 Y174.902 E.03098
G1 X154.466 Y116.498 E1.87806
G1 X141.594 Y116.498 E.41395
; COOLING_NODE: 0
M204 S250
G1 X141.926 Y116.89 F60000
M106 S127.5
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F2805
M204 S5000
G1 X141.926 Y174.51 E1.7163
G1 X142.889 Y174.51 E.02869
G1 X142.889 Y176.09 E.04706
G1 X139.111 Y176.09 E.11253
G1 X139.111 Y174.51 E.04706
G1 X140.074 Y174.51 E.02869
G1 X140.074 Y116.89 E1.7163
G1 X123.439 Y116.89 E.4955
M73 P67 R5
G1 X123.039 Y116.89 E.01191
G1 X122.639 Y116.89 E.01191
G1 X122.239 Y116.89 E.01191
G1 X121.839 Y116.89 E.01191
G1 X121.439 Y116.89 E.01191
G1 X121.039 Y116.89 E.01191
G1 X120.639 Y116.89 E.01191
G1 X120.239 Y116.89 E.01191
G1 X119.839 Y116.89 E.01191
G1 X119.439 Y116.89 E.01191
G1 F2364.214
G1 X119.039 Y116.89 E.01191
G1 F1800
G1 X118.67 Y116.89 E.01099
M106 S61.2
M106 S127.5
; FEATURE: Overhang wall
; LINE_WIDTH: 0.45
G1 F3000
G1 X117.33 Y116.89 E.04311
M106 S61.2
M106 S127.5
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F1800
G1 X116.961 Y116.89 E.01099
M106 S61.2
M106 S127.5
G1 F2364.214
G1 X116.561 Y116.89 E.01191
G1 F2805
G1 X116.161 Y116.89 E.01191
G1 X115.761 Y116.89 E.01191
G1 X115.361 Y116.89 E.01191
G1 X114.961 Y116.89 E.01191
G1 X114.561 Y116.89 E.01191
G1 X114.161 Y116.89 E.01191
G1 X113.761 Y116.89 E.01191
G1 X113.361 Y116.89 E.01191
G1 X112.961 Y116.89 E.01191
G1 X112.561 Y116.89 E.01191
G1 X111.21 Y116.89 E.04023
G1 X111.21 Y112.31 E.13642
G1 X112.561 Y112.31 E.04023
G1 X112.961 Y112.31 E.01191
G1 X113.361 Y112.31 E.01191
G1 X113.761 Y112.31 E.01191
G1 X114.161 Y112.31 E.01191
G1 X114.561 Y112.31 E.01191
G1 X114.961 Y112.31 E.01191
G1 X115.361 Y112.31 E.01191
G1 X115.761 Y112.31 E.01191
G1 X116.161 Y112.31 E.01191
G1 X116.561 Y112.31 E.01191
G1 F2364.214
G1 X116.961 Y112.31 E.01191
G1 F1800
G1 X117.33 Y112.31 E.01099
M106 S61.2
M106 S127.5
; FEATURE: Overhang wall
; LINE_WIDTH: 0.45
G1 F3000
G1 X118.67 Y112.31 E.04311
M106 S61.2
M106 S127.5
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F1800
G1 X119.039 Y112.31 E.01099
M106 S61.2
G1 F2364.214
G1 X119.439 Y112.31 E.01191
G1 F2805
G1 X119.839 Y112.31 E.01191
G1 X120.239 Y112.31 E.01191
G1 X120.639 Y112.31 E.01191
G1 X121.039 Y112.31 E.01191
G1 X121.439 Y112.31 E.01191
G1 X121.839 Y112.31 E.01191
G1 X122.239 Y112.31 E.01191
G1 X122.639 Y112.31 E.01191
G1 X123.039 Y112.31 E.01191
G1 X123.439 Y112.31 E.01191
G1 X158.79 Y112.31 E1.05298
G1 X158.79 Y116.89 E.13642
M106 S127.5
G1 X155.926 Y116.89 E.08532
G1 X155.926 Y174.51 E1.7163
G1 X156.889 Y174.51 E.02869
G1 X156.889 Y176.09 E.04706
G1 X153.111 Y176.09 E.11253
G1 X153.111 Y174.51 E.04706
G1 X154.074 Y174.51 E.02869
G1 X154.074 Y116.89 E1.7163
G1 X141.986 Y116.89 E.36008
; WIPE_START
G1 F12000
M204 S8000
G1 X141.985 Y117.89 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I.654 J-1.026 P1  F60000
G1 X136.192 Y114.198 Z2.8
G1 Z2.4
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X136.192 Y113.864 E.01074
G1 X135.263 Y113.864 E.02987
G1 X134.869 Y115.336 E.04897
G1 X134.137 Y115.336 E.02353
G1 X132.666 Y113.864 E.0669
M204 S10000
G1 X132.709 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X132.315 Y115.336 E.04897
G1 X132.393 Y115.336 E.0025
G1 X130.921 Y113.864 E.0669
G1 X131.432 Y113.864 E.01641
G1 X131.038 Y115.336 E.04897
G1 X130.648 Y115.336 E.01253
G1 X129.177 Y113.864 E.0669
G1 X130.155 Y113.864 E.03144
G1 X129.761 Y115.336 E.04897
G1 X130.444 Y115.336 E.02199
; WIPE_START
G1 X129.761 Y115.336 E-.2599
G1 X129.842 Y115.03 E-.1201
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I-.376 J-1.157 P1  F60000
G1 X128.903 Y115.336 Z2.8
G1 Z2.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X127.432 Y113.864 E.0669
M204 S10000
G1 X127.601 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X127.206 Y115.336 E.04897
G1 X125.688 Y113.864 E.06799
G1 X126.323 Y113.864 E.02044
G1 X125.929 Y115.336 E.04897
G1 X125.414 Y115.336 E.01656
G1 X123.943 Y113.864 E.0669
G1 X121.575 Y114.487 E.07875
G1 X121.575 Y114.985 E.01601
G1 X121.925 Y115.336 E.01593
G1 X122.098 Y115.336 E.00555
G1 X122.492 Y113.864 E.04897
G1 X122.199 Y113.864 E.00943
G1 X123.67 Y115.336 E.0669
; WIPE_START
G1 X122.963 Y114.628 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I.993 J.703 P1  F60000
G1 X123.503 Y113.864 Z2.8
G1 Z2.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X123.769 Y113.864 E.00855
G1 X123.375 Y115.336 E.04897
G1 X123.176 Y115.336 E.00641
G1 X128.666 Y113.864 E.18277
G1 X128.878 Y113.864 E.00681
G1 X128.483 Y115.336 E.04897
; WIPE_START
G1 X128.742 Y114.37 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I-.714 J-.985 P1  F60000
G1 X127.41 Y115.336 Z2.8
G1 Z2.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X127.942 Y115.336 E.01711
G1 X133.432 Y113.864 E.18277
G1 X133.782 Y113.864 E.01127
; WIPE_START
G1 X133.432 Y113.864 E-.13313
G1 X132.805 Y114.033 E-.24687
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I-1.042 J.629 P1  F60000
G1 X133.592 Y115.336 Z2.8
G1 Z2.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X133.986 Y113.864 E.04897
G1 X134.411 Y113.864 E.01365
G1 X135.882 Y115.336 E.0669
G1 X136.192 Y115.336 E.00998
G1 X136.192 Y114.402 E.03002
G1 X132.708 Y115.336 E.11598
G1 X133.105 Y115.336 E.01275
; WIPE_START
G1 X132.708 Y115.336 E-.15066
G1 X133.291 Y115.179 E-.22934
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I-.024 J-1.217 P1  F60000
G1 X125.211 Y115.336 Z2.8
G1 Z2.4
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X124.652 Y115.336 E.01797
G1 X125.046 Y113.864 E.04897
G1 X124.147 Y113.864 E.02892
; WIPE_START
G1 X125.046 Y113.864 E-.3418
M73 P67 R4
G1 X125.02 Y113.962 E-.0382
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I.025 J-1.217 P1  F60000
G1 X121.353 Y113.887 Z2.8
G1 Z2.4
G1 E.4 F1800
; FEATURE: Bridge
; LINE_WIDTH: 0.4954
G1 F3000
M204 S8000
G1 X114.761 Y113.887 E.2356
G1 X114.761 Y114.34 E.01617
G1 X121.183 Y114.34 E.22954
G1 X121.183 Y114.792 E.01617
G1 X114.761 Y114.792 E.22954
G1 X114.761 Y115.245 E.01617
G1 X121.353 Y115.245 E.2356
M106 S61.2
; WIPE_START
G1 X120.353 Y115.245 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I-.01 J-1.217 P1  F60000
G1 X114.384 Y115.292 Z2.8
G1 Z2.4
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X114.384 Y113.908 E.04121
G1 X112.808 Y113.908 E.04693
G1 X112.808 Y115.292 E.04121
G1 X114.324 Y115.292 E.04514
M204 S10000
G1 X113.944 Y114.852 F60000
; LINE_WIDTH: 0.54612
M73 P68 R4
G1 F10731.32
M204 S8000
G1 X113.944 Y114.348 E.02
G1 X113.248 Y114.348 E.02764
G1 X113.248 Y114.852 E.02
G1 X113.884 Y114.852 E.02526
; WIPE_START
G1 X113.248 Y114.852 E-.24144
G1 X113.248 Y114.487 E-.13856
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I-.003 J1.217 P1  F60000
G1 X157.192 Y114.6 Z2.8
G1 Z2.4
G1 E.4 F1800
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.41999
G1 F12000
M204 S8000
G1 X157.192 Y113.908 E.0206
G1 X136.584 Y113.908 E.61381
G1 X136.584 Y115.292 E.04121
G1 X157.192 Y115.292 E.61381
G1 X157.192 Y114.66 E.01882
; WIPE_START
G1 X157.192 Y115.292 E-.24006
G1 X156.823 Y115.292 E-.13994
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I.027 J-1.217 P1  F60000
G1 X137.024 Y114.852 Z2.8
G1 Z2.4
G1 E.4 F1800
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X156.752 Y114.852 E.78415
G1 X156.752 Y114.348 E.02
G1 X137.024 Y114.348 E.78415
G1 X137.024 Y114.792 E.01762
; WIPE_START
G1 X137.024 Y114.348 E-.16842
G1 X137.581 Y114.348 E-.21158
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I-1.216 J.042 P1  F60000
G1 X139.707 Y175.3 Z2.8
G1 Z2.4
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.43172
G1 F13888.888
M204 S8000
G1 X140.67 Y175.3 E.02958
M204 S10000
G1 X141.33 Y175.3 F60000
G1 F13888.888
M204 S8000
G1 X142.293 Y175.3 E.02958
; WIPE_START
G1 X141.33 Y175.3 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z2.8 I0 J1.217 P1  F60000
G1 X153.707 Y175.3 Z2.8
G1 Z2.4
G1 E.4 F1800
G1 F13888.888
M204 S8000
G1 X154.67 Y175.3 E.02958
M204 S10000
G1 X155.33 Y175.3 F60000
G1 F13888.888
M204 S8000
G1 X156.293 Y175.3 E.02958
; CHANGE_LAYER
; Z_HEIGHT: 2.6
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F13888.888
G1 X155.33 Y175.3 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 13/27
; update layer progress
M73 L13
M991 S0 P12 ;notify layer change
; OBJECT_ID: 16
; COOLING_NODE: 0
; start printing object, unique label id: 16
M624 BAAAAAAAAAA=
M204 S10000
G17
G3 Z2.8 I-.095 J1.213 P1  F60000
G1 X195.157 Y178.407 Z2.8
G1 Z2.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X194.745 Y178.402 E.01326
G3 X194.575 Y171.609 I.255 J-3.405 E.32309
G1 X194.915 Y171.583 E.01097
G3 X195.255 Y178.402 I.085 J3.414 E.33949
G1 X195.217 Y178.404 E.00122
; COOLING_NODE: 0
M204 S10000
G1 X195.156 Y178.001 F60000
G1 F13265.217
M204 S8000
G1 X194.776 Y177.997 E.01223
G3 X194.625 Y172.013 I.224 J-3 E.28458
G1 X194.925 Y171.991 E.00966
G3 X195.225 Y177.997 I.075 J3.007 E.29902
G1 X195.216 Y177.998 E.00029
; COOLING_NODE: 0
M204 S10000
G1 X195.155 Y177.595 F60000
G1 F13265.217
M204 S8000
G1 X194.806 Y177.592 E.01122
G3 X194.676 Y172.417 I.194 J-2.594 E.24606
G1 X194.935 Y172.398 E.00835
G3 X195.215 Y177.59 I.065 J2.6 E.25791
; COOLING_NODE: 0
M204 S250
G1 X195.154 Y177.204 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X194.835 Y177.201 E.00951
G3 X194.725 Y172.807 I.165 J-2.203 E.19358
G1 X194.945 Y172.79 E.00657
G3 X195.214 Y177.197 I.055 J2.208 E.20194
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X194.835 Y177.201 E-.14384
G1 X194.401 Y177.128 E-.16718
G1 X194.232 Y177.061 E-.06898
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I-1.086 J.55 P1  F60000
G1 X201.584 Y191.584 Z3
G1 Z2.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y191.584 E.42342
G1 X188.416 Y170.416 E.68067
G1 X201.584 Y170.416 E.42342
G1 X201.584 Y191.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y191.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y191.991 E.4496
G1 X188.009 Y170.009 E.70685
G1 X201.991 Y170.009 E.4496
G1 X201.991 Y191.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y192.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y192.398 E.47578
G1 X187.602 Y169.602 E.73303
G1 X202.398 Y169.602 E.47578
G1 X202.398 Y192.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y192.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y192.79 E.46408
G1 X187.21 Y169.21 E.70237
G1 X202.79 Y169.21 E.46408
G1 X202.79 Y192.73 E.70058
; object ids of layer 13 start: 8,12,16
M624 BwAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer13 end: 8,12,16
M625
; WIPE_START
M204 S8000
G1 X201.79 Y192.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I1.215 J-.077 P1  F60000
G1 X201.42 Y186.884 Z3
G1 Z2.6
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42179
G1 F14252.909
M204 S8000
G1 X188.749 Y174.213 E.53628
G1 X188.749 Y174.749 E.01604
G1 X201.251 Y187.25 E.5291
G1 X201.251 Y187.786 E.01604
G1 X188.749 Y175.285 E.5291
G1 X188.749 Y175.821 E.01604
G1 X201.251 Y188.322 E.5291
G1 X201.251 Y188.858 E.01604
G1 X188.749 Y176.357 E.5291
G1 X188.749 Y176.892 E.01604
G1 X201.251 Y189.393 E.5291
G1 X201.251 Y189.929 E.01604
G1 X188.749 Y177.428 E.5291
G1 X188.749 Y177.964 E.01604
G1 X201.251 Y190.465 E.5291
G1 X201.251 Y191.001 E.01604
G1 X188.749 Y178.5 E.5291
G1 X188.749 Y179.036 E.01604
G1 X200.964 Y191.251 E.51699
G1 X200.429 Y191.251 E.01604
G1 X188.749 Y179.571 E.49431
G1 X188.749 Y180.107 E.01604
G1 X199.893 Y191.251 E.47164
G1 X199.357 Y191.251 E.01604
G1 X188.749 Y180.643 E.44896
G1 X188.749 Y181.179 E.01604
G1 X198.821 Y191.251 E.42628
G1 X198.285 Y191.251 E.01604
G1 X188.749 Y181.715 E.4036
G1 X188.749 Y182.25 E.01604
G1 X197.75 Y191.251 E.38093
G1 X197.214 Y191.251 E.01604
G1 X188.749 Y182.786 E.35825
G1 X188.749 Y183.322 E.01604
G1 X196.678 Y191.251 E.33557
G1 X196.142 Y191.251 E.01604
G1 X188.749 Y183.858 E.31289
G1 X188.749 Y184.394 E.01604
G1 X195.606 Y191.251 E.29022
G1 X195.071 Y191.251 E.01604
G1 X188.749 Y184.929 E.26754
G1 X188.749 Y185.465 E.01604
G1 X194.535 Y191.251 E.24486
G1 X193.999 Y191.251 E.01604
G1 X188.749 Y186.001 E.22218
G1 X188.749 Y186.537 E.01604
G1 X193.463 Y191.251 E.19951
G1 X192.927 Y191.251 E.01604
G1 X188.749 Y187.073 E.17683
G1 X188.749 Y187.608 E.01604
G1 X192.392 Y191.251 E.15415
G1 X191.856 Y191.251 E.01604
G1 X188.749 Y188.144 E.13147
G1 X188.749 Y188.68 E.01604
G1 X191.32 Y191.251 E.10879
G1 X190.784 Y191.251 E.01604
G1 X188.749 Y189.216 E.08612
G1 X188.749 Y189.752 E.01604
G1 X190.248 Y191.251 E.06344
G1 X189.713 Y191.251 E.01604
G1 X188.749 Y190.287 E.04076
G1 X188.749 Y190.823 E.01604
G1 X189.346 Y191.42 E.02527
; WIPE_START
G1 X188.749 Y190.823 E-.3208
G1 X188.749 Y190.667 E-.0592
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I1.157 J.377 P1  F60000
G1 X195.296 Y170.58 Z3
G1 Z2.6
G1 E.4 F1800
G1 F14252.909
M204 S8000
G1 X196.15 Y171.434 E.03613
G2 X195.462 Y171.282 I-1.156 J3.603 E.02111
G1 X194.93 Y170.749 E.02252
G1 X194.394 Y170.749 E.01604
G1 X194.895 Y171.25 E.0212
G2 X194.408 Y171.3 I.002 J2.456 E.01466
G1 X193.858 Y170.749 E.02328
G1 X193.323 Y170.749 E.01604
G1 X193.97 Y171.397 E.02742
G2 X193.572 Y171.535 I.488 J2.054 E.01263
G1 X192.787 Y170.749 E.03325
G1 X192.251 Y170.749 E.01604
G1 X193.209 Y171.707 E.04055
G2 X192.877 Y171.911 I.847 J1.757 E.01168
G1 X191.715 Y170.749 E.04916
G1 X191.179 Y170.749 E.01604
G1 X192.573 Y172.143 E.05898
G2 X192.302 Y172.408 I.905 J1.193 E.01137
G1 X190.644 Y170.749 E.07021
G1 X190.108 Y170.749 E.01604
G1 X192.049 Y172.691 E.08215
G2 X191.828 Y173.005 I1.461 J1.261 E.01153
G1 X189.572 Y170.749 E.09547
G1 X189.036 Y170.749 E.01604
G1 X191.636 Y173.349 E.11004
G2 X191.476 Y173.726 I1.798 J.985 E.01225
G1 X188.749 Y170.999 E.11542
G1 X188.749 Y171.534 E.01604
G1 X191.353 Y174.138 E.11019
G2 X191.272 Y174.593 I2.233 J.632 E.01385
G1 X188.749 Y172.07 E.10677
G1 X188.749 Y172.606 E.01604
G1 X191.254 Y175.11 E.106
G2 X191.318 Y175.71 I3.028 J-.019 E.01808
G1 X188.749 Y173.142 E.1087
G1 X188.749 Y173.678 E.01604
G1 X191.556 Y176.484 E.11878
G2 X193.511 Y178.439 I3.416 J-1.461 E.08478
G1 X201.251 Y186.179 E.32759
G1 X201.251 Y185.643 E.01604
G1 X194.289 Y178.681 E.29466
G2 X194.889 Y178.745 I.746 J-4.124 E.01808
G1 X201.251 Y185.107 E.26925
G1 X201.251 Y184.571 E.01604
G1 X195.405 Y178.725 E.24742
G2 X195.864 Y178.649 I-.604 J-5.077 E.01395
G1 X201.251 Y184.035 E.22797
G1 X201.251 Y183.5 E.01604
G1 X196.276 Y178.525 E.21057
G2 X196.651 Y178.364 I-.613 J-1.956 E.01224
G1 X201.251 Y182.964 E.19467
G1 X201.251 Y182.428 E.01604
G1 X196.995 Y178.172 E.18013
M73 P69 R4
G2 X197.309 Y177.951 I-.948 J-1.682 E.01153
G1 X201.251 Y181.892 E.16681
G1 X201.251 Y181.356 E.01604
G1 X197.596 Y177.702 E.15467
G2 X197.856 Y177.426 I-1.25 J-1.436 E.01136
G1 X201.251 Y180.821 E.14368
G1 X201.251 Y180.285 E.01604
G1 X198.088 Y177.122 E.13385
G2 X198.292 Y176.79 I-1.554 J-1.181 E.01168
G1 X201.251 Y179.749 E.12523
G1 X201.251 Y179.213 E.01604
G1 X198.46 Y176.423 E.11812
G2 X198.604 Y176.031 I-1.44 J-.753 E.01252
G1 X201.251 Y178.677 E.11201
G1 X201.251 Y178.142 E.01604
G1 X198.7 Y175.591 E.10794
G2 X198.747 Y175.102 I-2.422 J-.477 E.01474
G1 X201.251 Y177.606 E.10598
G1 X201.251 Y177.07 E.01604
G1 X198.72 Y174.539 E.10711
G2 X198.57 Y173.854 I-4.399 J.601 E.02101
G1 X201.251 Y176.534 E.11344
G1 X201.251 Y175.998 E.01604
G1 X196.002 Y170.749 E.22216
G1 X196.537 Y170.749 E.01604
G1 X201.251 Y175.463 E.19948
G1 X201.251 Y174.927 E.01604
G1 X197.073 Y170.749 E.1768
G1 X197.609 Y170.749 E.01604
G1 X201.251 Y174.391 E.15413
G1 X201.251 Y173.855 E.01604
G1 X198.145 Y170.749 E.13145
G1 X198.681 Y170.749 E.01604
G1 X201.251 Y173.319 E.10877
G1 X201.251 Y172.784 E.01604
G1 X199.216 Y170.749 E.08609
G1 X199.752 Y170.749 E.01604
G1 X201.251 Y172.248 E.06342
G1 X201.251 Y171.712 E.01604
G1 X200.288 Y170.749 E.04074
G1 X200.824 Y170.749 E.01604
G1 X201.42 Y171.346 E.02524
; OBJECT_ID: 12
; COOLING_NODE: 0
; WIPE_START
G1 X200.824 Y170.749 E-.3205
G1 X200.667 Y170.749 E-.0595
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 16
M625
; start printing object, unique label id: 12
M624 AgAAAAAAAAA=
M204 S10000
G17
G3 Z3 I1.215 J-.073 P1  F60000
G1 X197.45 Y117.379 Z3
G1 Z2.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X197.258 Y117.559 E.00845
G3 X194.575 Y111.609 I-2.258 J-2.562 E.41063
G1 X194.915 Y111.583 E.01095
G3 X197.502 Y117.321 I.085 J3.414 E.25743
G1 X197.49 Y117.335 E.00058
; COOLING_NODE: 0
M204 S10000
G1 X197.166 Y117.088 F60000
G1 F13265.217
M204 S8000
G1 X196.989 Y117.254 E.0078
G3 X194.626 Y112.013 I-1.989 J-2.256 E.36168
G1 X194.925 Y111.991 E.00965
G3 X197.205 Y117.043 I.075 J3.007 E.22667
; COOLING_NODE: 0
M204 S10000
G1 X196.881 Y116.796 F60000
G1 F13265.217
M204 S8000
G1 X196.72 Y116.949 E.00714
G3 X194.676 Y112.417 I-1.72 J-1.951 E.31274
G1 X194.935 Y112.398 E.00834
G3 X196.921 Y116.751 I.065 J2.6 E.19533
; COOLING_NODE: 0
M204 S250
G1 X196.607 Y116.515 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X196.289 Y116.792 E.01256
G3 X194.725 Y112.807 I-1.289 J-1.794 E.23947
G1 X194.945 Y112.79 E.00656
G3 X196.647 Y116.471 I.055 J2.208 E.15298
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X196.289 Y116.792 E-.18288
G1 X195.909 Y117.015 E-.16722
G1 X195.834 Y117.04 E-.0299
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I-1.132 J.447 P1  F60000
G1 X201.584 Y131.584 Z3
G1 Z2.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y131.584 E.42342
G1 X188.416 Y110.416 E.68067
G1 X201.584 Y110.416 E.42342
G1 X201.584 Y131.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y131.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y131.991 E.4496
G1 X188.009 Y110.009 E.70685
G1 X201.991 Y110.009 E.4496
G1 X201.991 Y131.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y132.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y132.398 E.47578
G1 X187.602 Y109.602 E.73303
G1 X202.398 Y109.602 E.47578
G1 X202.398 Y132.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y132.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y132.79 E.46408
G1 X187.21 Y109.21 E.70237
G1 X202.79 Y109.21 E.46408
G1 X202.79 Y132.73 E.70058
; WIPE_START
M204 S8000
G1 X201.79 Y132.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I1.215 J-.077 P1  F60000
G1 X201.42 Y126.884 Z3
G1 Z2.6
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42179
G1 F14252.909
M204 S8000
G1 X188.749 Y114.213 E.53628
G1 X188.749 Y114.749 E.01604
G1 X201.251 Y127.25 E.5291
G1 X201.251 Y127.786 E.01604
G1 X188.749 Y115.285 E.5291
G1 X188.749 Y115.821 E.01604
G1 X201.251 Y128.322 E.5291
G1 X201.251 Y128.858 E.01604
G1 X188.749 Y116.357 E.5291
G1 X188.749 Y116.892 E.01604
G1 X201.251 Y129.393 E.5291
G1 X201.251 Y129.929 E.01604
G1 X188.749 Y117.428 E.5291
G1 X188.749 Y117.964 E.01604
G1 X201.251 Y130.465 E.5291
G1 X201.251 Y131.001 E.01604
G1 X188.749 Y118.5 E.5291
G1 X188.749 Y119.036 E.01604
G1 X200.964 Y131.251 E.51699
G1 X200.429 Y131.251 E.01604
G1 X188.749 Y119.571 E.49431
G1 X188.749 Y120.107 E.01604
G1 X199.893 Y131.251 E.47164
G1 X199.357 Y131.251 E.01604
G1 X188.749 Y120.643 E.44896
G1 X188.749 Y121.179 E.01604
G1 X198.821 Y131.251 E.42628
G1 X198.285 Y131.251 E.01604
G1 X188.749 Y121.715 E.4036
G1 X188.749 Y122.25 E.01604
G1 X197.75 Y131.251 E.38093
G1 X197.214 Y131.251 E.01604
G1 X188.749 Y122.786 E.35825
G1 X188.749 Y123.322 E.01604
G1 X196.678 Y131.251 E.33557
G1 X196.142 Y131.251 E.01604
G1 X188.749 Y123.858 E.31289
G1 X188.749 Y124.394 E.01604
G1 X195.606 Y131.251 E.29022
G1 X195.071 Y131.251 E.01604
G1 X188.749 Y124.929 E.26754
G1 X188.749 Y125.465 E.01604
G1 X194.535 Y131.251 E.24486
G1 X193.999 Y131.251 E.01604
G1 X188.749 Y126.001 E.22218
G1 X188.749 Y126.537 E.01604
G1 X193.463 Y131.251 E.19951
G1 X192.927 Y131.251 E.01604
G1 X188.749 Y127.073 E.17683
G1 X188.749 Y127.608 E.01604
G1 X192.392 Y131.251 E.15415
G1 X191.856 Y131.251 E.01604
G1 X188.749 Y128.144 E.13147
G1 X188.749 Y128.68 E.01604
G1 X191.32 Y131.251 E.10879
G1 X190.784 Y131.251 E.01604
G1 X188.749 Y129.216 E.08612
G1 X188.749 Y129.752 E.01604
G1 X190.248 Y131.251 E.06344
G1 X189.713 Y131.251 E.01604
G1 X188.749 Y130.287 E.04076
G1 X188.749 Y130.823 E.01604
G1 X189.346 Y131.42 E.02527
; WIPE_START
G1 X188.749 Y130.823 E-.3208
G1 X188.749 Y130.667 E-.0592
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I1.157 J.377 P1  F60000
G1 X195.296 Y110.58 Z3
G1 Z2.6
G1 E.4 F1800
G1 F14252.909
M204 S8000
G1 X196.15 Y111.434 E.03613
G2 X195.462 Y111.282 I-1.156 J3.602 E.02111
G1 X194.93 Y110.749 E.02252
G1 X194.394 Y110.749 E.01604
G1 X194.895 Y111.25 E.0212
G2 X194.408 Y111.3 I.002 J2.459 E.01466
G1 X193.858 Y110.749 E.02328
G1 X193.323 Y110.749 E.01604
G1 X193.97 Y111.397 E.02742
G2 X193.572 Y111.535 I.491 J2.062 E.01263
G1 X192.787 Y110.749 E.03325
G1 X192.251 Y110.749 E.01604
G1 X193.209 Y111.707 E.04055
G2 X192.877 Y111.911 I.849 J1.761 E.01168
G1 X191.715 Y110.749 E.04916
G1 X191.179 Y110.749 E.01604
G1 X192.573 Y112.143 E.05898
G2 X192.302 Y112.408 I.905 J1.193 E.01137
G1 X190.644 Y110.749 E.07021
G1 X190.108 Y110.749 E.01604
G1 X192.049 Y112.691 E.08215
G2 X191.828 Y113.005 I1.462 J1.262 E.01153
G1 X189.572 Y110.749 E.09548
G1 X189.036 Y110.749 E.01604
G1 X191.636 Y113.349 E.11004
G2 X191.476 Y113.726 I1.799 J.986 E.01225
G1 X188.749 Y110.999 E.11542
G1 X188.749 Y111.534 E.01604
G1 X191.353 Y114.138 E.11019
G2 X191.272 Y114.593 I2.233 J.632 E.01385
G1 X188.749 Y112.07 E.10677
G1 X188.749 Y112.606 E.01604
G1 X191.254 Y115.11 E.106
G2 X191.318 Y115.71 I3.03 J-.02 E.01808
G1 X188.749 Y113.142 E.1087
G1 X188.749 Y113.678 E.01604
G1 X191.556 Y116.484 E.11878
G2 X193.511 Y118.439 I3.416 J-1.461 E.08478
G1 X201.251 Y126.179 E.32759
G1 X201.251 Y125.643 E.01604
G1 X194.289 Y118.681 E.29466
G2 X194.889 Y118.745 I.746 J-4.125 E.01808
G1 X201.251 Y125.107 E.26925
G1 X201.251 Y124.571 E.01604
G1 X195.405 Y118.725 E.24742
G2 X195.864 Y118.649 I-.61 J-5.117 E.01395
G1 X201.251 Y124.035 E.22797
G1 X201.251 Y123.5 E.01604
G1 X196.275 Y118.525 E.21057
G2 X196.651 Y118.364 I-.612 J-1.954 E.01224
G1 X201.251 Y122.964 E.19467
G1 X201.251 Y122.428 E.01604
G1 X196.995 Y118.172 E.18013
G2 X197.309 Y117.951 I-.949 J-1.684 E.01153
G1 X201.251 Y121.892 E.16681
G1 X201.251 Y121.356 E.01604
G1 X197.596 Y117.702 E.15467
G2 X197.856 Y117.426 I-1.25 J-1.435 E.01136
G1 X201.251 Y120.821 E.14368
G1 X201.251 Y120.285 E.01604
G1 X198.088 Y117.122 E.13385
G2 X198.292 Y116.79 I-1.554 J-1.181 E.01168
G1 X201.251 Y119.749 E.12523
G1 X201.251 Y119.213 E.01604
G1 X198.46 Y116.422 E.11812
G2 X198.604 Y116.031 I-1.44 J-.753 E.01252
G1 X201.251 Y118.677 E.11201
G1 X201.251 Y118.142 E.01604
M73 P70 R4
G1 X198.7 Y115.591 E.10794
G2 X198.747 Y115.102 I-2.422 J-.477 E.01474
G1 X201.251 Y117.606 E.10598
G1 X201.251 Y117.07 E.01604
G1 X198.72 Y114.539 E.10711
G2 X198.57 Y113.854 I-4.4 J.601 E.02101
G1 X201.251 Y116.534 E.11344
G1 X201.251 Y115.998 E.01604
G1 X196.002 Y110.749 E.22216
G1 X196.537 Y110.749 E.01604
G1 X201.251 Y115.463 E.19948
G1 X201.251 Y114.927 E.01604
G1 X197.073 Y110.749 E.1768
G1 X197.609 Y110.749 E.01604
G1 X201.251 Y114.391 E.15413
G1 X201.251 Y113.855 E.01604
G1 X198.145 Y110.749 E.13145
G1 X198.681 Y110.749 E.01604
G1 X201.251 Y113.319 E.10877
G1 X201.251 Y112.784 E.01604
G1 X199.216 Y110.749 E.08609
G1 X199.752 Y110.749 E.01604
G1 X201.251 Y112.248 E.06342
G1 X201.251 Y111.712 E.01604
G1 X200.288 Y110.749 E.04074
G1 X200.824 Y110.749 E.01604
G1 X201.42 Y111.346 E.02524
; OBJECT_ID: 8
; COOLING_NODE: 0
; WIPE_START
G1 X200.824 Y110.749 E-.3205
G1 X200.667 Y110.749 E-.0595
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 12
M625
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z3 I-.079 J-1.214 P1  F60000
G1 X139.288 Y114.72 Z3
G1 Z2.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X137.711 Y114.72 E.05071
G1 X137.711 Y115.684 E.031
G1 X112.416 Y115.684 E.81339
G1 X112.416 Y113.516 E.0697
G1 X157.584 Y113.516 E1.45243
G1 X157.584 Y114.72 E.0387
G1 X151.711 Y114.72 E.18885
G1 X151.711 Y115.684 E.031
G1 X144.289 Y115.684 E.23867
G1 X144.289 Y114.72 E.031
G1 X139.348 Y114.72 E.15888
; COOLING_NODE: 0
M204 S10000
G1 X139.695 Y115.127 F60000
G1 F13265.217
M204 S8000
G1 X138.118 Y115.127 E.05071
G1 X138.118 Y116.091 E.031
G1 X112.009 Y116.091 E.83957
G1 X112.009 Y113.109 E.09588
G1 X157.991 Y113.109 E1.47861
G1 X157.991 Y115.127 E.06488
G1 X152.118 Y115.127 E.18885
G1 X152.118 Y116.091 E.031
G1 X143.882 Y116.091 E.26485
G1 X143.882 Y115.127 E.031
G1 X139.755 Y115.127 E.1327
; COOLING_NODE: 0
M204 S10000
G1 X140.102 Y115.534 F60000
G1 F13265.217
M204 S8000
G1 X138.525 Y115.534 E.05071
G1 X138.525 Y116.498 E.031
G1 X111.602 Y116.498 E.86575
G1 X111.602 Y112.702 E.12206
G1 X158.398 Y112.702 E1.50479
G1 X158.398 Y116.498 E.12206
G1 X157.475 Y116.498 E.02969
G1 X157.475 Y115.534 E.031
G1 X152.525 Y115.534 E.15916
G1 X152.525 Y116.498 E.031
G1 X143.475 Y116.498 E.29103
G1 X143.475 Y115.534 E.031
G1 X140.162 Y115.534 E.10652
; COOLING_NODE: 0
; WIPE_START
G1 X139.162 Y115.534 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I-.619 J1.048 P1  F60000
G1 X141.458 Y116.89 Z3
G1 Z2.6
G1 E.4 F1800
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F2657
M204 S5000
G1 X141.458 Y174.51 E1.7163
G1 X142.678 Y174.51 E.03633
G1 X142.678 Y176.09 E.04706
G1 X139.322 Y176.09 E.09998
G1 X139.322 Y174.51 E.04706
G1 X140.542 Y174.51 E.03633
G1 X140.542 Y116.89 E1.7163
G1 X111.21 Y116.89 E.87369
G1 X111.21 Y112.31 E.13642
G1 X158.79 Y112.31 E1.41725
G1 X158.79 Y116.89 E.13642
G1 X155.458 Y116.89 E.09924
G1 X155.458 Y174.51 E1.7163
G1 X156.678 Y174.51 E.03633
G1 X156.678 Y176.09 E.04706
M73 P71 R4
G1 X153.322 Y176.09 E.09998
G1 X153.322 Y174.51 E.04706
G1 X154.542 Y174.51 E.03633
G1 X154.542 Y116.89 E1.7163
G1 X141.518 Y116.89 E.38792
; WIPE_START
G1 F12000
M204 S8000
G1 X141.517 Y117.89 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I1.082 J.557 P1  F60000
G1 X142.617 Y115.756 Z3
G1 Z2.6
G1 E.4 F1800
; FEATURE: Top surface
G1 F12000
M204 S2000
G1 X143.252 Y116.392 E.02677
G1 X143.386 Y116.525
G1 X143.144 Y116.816
G1 X143.01 Y116.683
G1 X142.084 Y115.756 E.03902
G1 X141.95 Y115.623
G1 X141.417 Y115.623
G1 X141.55 Y115.756
G1 X142.477 Y116.683 E.03902
G1 X142.61 Y116.816
G1 X142.077 Y116.816
G1 X141.943 Y116.683
G1 X141.017 Y115.756 E.03902
G1 X140.883 Y115.623
G1 X140.35 Y115.623
G1 X140.484 Y115.756
G1 X141.41 Y116.683 E.03902
G1 X141.544 Y116.816
G1 X141.385 Y117.19
G1 X141.251 Y117.057
G1 X139.951 Y115.756 E.05478
G1 X139.817 Y115.623
G1 X139.284 Y115.623
G1 X139.417 Y115.756
G1 X140.344 Y116.683 E.03902
G1 X140.477 Y116.816
G1 X139.944 Y116.816
G1 X139.81 Y116.683
G1 X138.884 Y115.756 E.03902
G1 X138.75 Y115.623
G1 X138.614 Y116.019
G1 X138.748 Y116.153
G1 X139.277 Y116.683 E.0223
; WIPE_START
M204 S8000
G1 X138.748 Y116.153 E-.28454
G1 X138.614 Y116.019 E-.07182
G1 X138.634 Y115.961 E-.02364
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I-.572 J1.074 P1  F60000
G1 X140.749 Y117.088 Z3
G1 Z2.6
G1 E.4 F1800
G1 F12000
M204 S2000
G1 X141.251 Y117.59 E.02115
G1 X141.385 Y117.724
G1 X141.385 Y118.257
G1 X141.251 Y118.123
G1 X140.749 Y117.621 E.02115
G1 X140.615 Y117.487
G1 X140.615 Y118.021
G1 X140.749 Y118.154
G1 X141.251 Y118.656 E.02115
G1 X141.385 Y118.79
G1 X141.385 Y119.323
G1 X141.251 Y119.19
G1 X140.749 Y118.688 E.02115
G1 X140.615 Y118.554
G1 X140.615 Y119.087
G1 X140.749 Y119.221
G1 X141.251 Y119.723 E.02115
G1 X141.385 Y119.857
G1 X141.385 Y120.39
G1 X141.251 Y120.256
G1 X140.749 Y119.754 E.02115
G1 X140.615 Y119.621
G1 X140.615 Y120.154
G1 X140.749 Y120.287
G1 X141.251 Y120.789 E.02115
G1 X141.385 Y120.923
G1 X141.385 Y121.456
G1 X141.251 Y121.323
G1 X140.749 Y120.821 E.02115
G1 X140.615 Y120.687
G1 X140.615 Y121.22
G1 X140.749 Y121.354
G1 X141.251 Y121.856 E.02115
G1 X141.385 Y121.99
G1 X141.385 Y122.523
G1 X141.251 Y122.389
G1 X140.749 Y121.887 E.02115
G1 X140.615 Y121.754
G1 X140.615 Y122.287
G1 X140.749 Y122.42
G1 X141.251 Y122.923 E.02115
G1 X141.385 Y123.056
G1 X141.385 Y123.589
G1 X141.251 Y123.456
G1 X140.749 Y122.954 E.02115
G1 X140.615 Y122.82
G1 X140.615 Y123.353
G1 X140.749 Y123.487
G1 X141.251 Y123.989 E.02115
G1 X141.385 Y124.123
G1 X141.385 Y124.656
G1 X141.251 Y124.522
G1 X140.749 Y124.02 E.02115
G1 X140.615 Y123.887
G1 X140.615 Y124.42
G1 X140.749 Y124.553
G1 X141.251 Y125.056 E.02115
G1 X141.385 Y125.189
G1 X141.385 Y125.722
G1 X141.251 Y125.589
G1 X140.749 Y125.087 E.02115
G1 X140.615 Y124.953
G1 X140.615 Y125.486
G1 X140.749 Y125.62
G1 X141.251 Y126.122 E.02115
G1 X141.385 Y126.256
G1 X141.385 Y126.789
G1 X141.251 Y126.655
G1 X140.749 Y126.153 E.02115
G1 X140.615 Y126.02
G1 X140.615 Y126.553
G1 X140.749 Y126.686
G1 X141.251 Y127.189 E.02115
G1 X141.385 Y127.322
G1 X141.385 Y127.855
G1 X141.251 Y127.722
G1 X140.749 Y127.22 E.02115
G1 X140.615 Y127.086
G1 X140.615 Y127.619
G1 X140.749 Y127.753
G1 X141.251 Y128.255 E.02115
G1 X141.385 Y128.389
G1 X141.385 Y128.922
G1 X141.251 Y128.788
G1 X140.749 Y128.286 E.02115
G1 X140.615 Y128.153
G1 X140.615 Y128.686
G1 X140.749 Y128.82
G1 X141.251 Y129.322 E.02115
G1 X141.385 Y129.455
G1 X141.385 Y129.988
G1 X141.251 Y129.855
G1 X140.749 Y129.353 E.02115
G1 X140.615 Y129.219
G1 X140.615 Y129.752
G1 X140.749 Y129.886
G1 X141.251 Y130.388 E.02115
G1 X141.385 Y130.522
G1 X141.385 Y131.055
G1 X141.251 Y130.921
G1 X140.749 Y130.419 E.02115
G1 X140.615 Y130.286
G1 X140.615 Y130.819
G1 X140.749 Y130.953
G1 X141.251 Y131.455 E.02115
G1 X141.385 Y131.588
G1 X141.385 Y132.122
G1 X141.251 Y131.988
G1 X140.749 Y131.486 E.02115
G1 X140.615 Y131.352
G1 X140.615 Y131.885
G1 X140.749 Y132.019
G1 X141.251 Y132.521 E.02115
G1 X141.385 Y132.655
G1 X141.385 Y133.188
G1 X141.251 Y133.054
G1 X140.749 Y132.552 E.02115
G1 X140.615 Y132.419
G1 X140.615 Y132.952
G1 X140.749 Y133.086
G1 X141.251 Y133.588 E.02115
G1 X141.385 Y133.721
G1 X141.385 Y134.255
G1 X141.251 Y134.121
G1 X140.749 Y133.619 E.02115
G1 X140.615 Y133.485
G1 X140.615 Y134.018
G1 X140.749 Y134.152
G1 X141.251 Y134.654 E.02115
G1 X141.385 Y134.788
G1 X141.385 Y135.321
G1 X141.251 Y135.187
G1 X140.749 Y134.685 E.02115
G1 X140.615 Y134.552
G1 X140.615 Y135.085
G1 X140.749 Y135.219
G1 X141.251 Y135.721 E.02115
G1 X141.385 Y135.854
G1 X141.385 Y136.388
G1 X141.251 Y136.254
G1 X140.749 Y135.752 E.02115
G1 X140.615 Y135.618
G1 X140.615 Y136.151
G1 X140.749 Y136.285
G1 X141.251 Y136.787 E.02115
G1 X141.385 Y136.921
G1 X141.385 Y137.454
G1 X141.251 Y137.32
G1 X140.749 Y136.818 E.02115
G1 X140.615 Y136.685
G1 X140.615 Y137.218
G1 X140.749 Y137.352
G1 X141.251 Y137.854 E.02115
G1 X141.385 Y137.987
G1 X141.385 Y138.521
G1 X141.251 Y138.387
G1 X140.749 Y137.885 E.02115
G1 X140.615 Y137.751
G1 X140.615 Y138.285
G1 X140.749 Y138.418
G1 X141.251 Y138.92 E.02115
G1 X141.385 Y139.054
G1 X141.385 Y139.587
G1 X141.251 Y139.453
G1 X140.749 Y138.951 E.02115
G1 X140.615 Y138.818
G1 X140.615 Y139.351
G1 X140.749 Y139.485
G1 X141.251 Y139.987 E.02115
G1 X141.385 Y140.12
G1 X141.385 Y140.654
G1 X141.251 Y140.52
G1 X140.749 Y140.018 E.02115
G1 X140.615 Y139.884
G1 X140.615 Y140.418
G1 X140.749 Y140.551
G1 X141.251 Y141.053 E.02115
G1 X141.385 Y141.187
G1 X141.385 Y141.72
G1 X141.251 Y141.587
G1 X140.749 Y141.084 E.02115
G1 X140.615 Y140.951
G1 X140.615 Y141.484
G1 X140.749 Y141.618
G1 X141.251 Y142.12 E.02115
G1 X141.385 Y142.253
G1 X141.385 Y142.787
G1 X141.251 Y142.653
G1 X140.749 Y142.151 E.02115
G1 X140.615 Y142.017
G1 X140.615 Y142.551
G1 X140.749 Y142.684
G1 X141.251 Y143.186 E.02115
G1 X141.385 Y143.32
G1 X141.385 Y143.853
G1 X141.251 Y143.72
G1 X140.749 Y143.217 E.02115
G1 X140.615 Y143.084
G1 X140.615 Y143.617
G1 X140.749 Y143.751
G1 X141.251 Y144.253 E.02115
G1 X141.385 Y144.386
G1 X141.385 Y144.92
G1 X141.251 Y144.786
G1 X140.749 Y144.284 E.02115
G1 X140.615 Y144.15
G1 X140.615 Y144.684
G1 X140.749 Y144.817
G1 X141.251 Y145.319 E.02115
G1 X141.385 Y145.453
G1 X141.385 Y145.986
G1 X141.251 Y145.853
G1 X140.749 Y145.351 E.02115
G1 X140.615 Y145.217
G1 X140.615 Y145.75
G1 X140.749 Y145.884
G1 X141.251 Y146.386 E.02115
G1 X141.385 Y146.519
G1 X141.385 Y147.053
G1 X141.251 Y146.919
G1 X140.749 Y146.417 E.02115
G1 X140.615 Y146.283
G1 X140.615 Y146.817
G1 X140.749 Y146.95
G1 X141.251 Y147.452 E.02115
G1 X141.385 Y147.586
G1 X141.385 Y148.119
G1 X141.251 Y147.986
G1 X140.749 Y147.484 E.02115
G1 X140.615 Y147.35
G1 X140.615 Y147.883
G1 X140.749 Y148.017
G1 X141.251 Y148.519 E.02115
G1 X141.385 Y148.653
G1 X141.385 Y149.186
G1 X141.251 Y149.052
G1 X140.749 Y148.55 E.02115
G1 X140.615 Y148.416
G1 X140.615 Y148.95
G1 X140.749 Y149.083
G1 X141.251 Y149.585 E.02115
G1 X141.385 Y149.719
G1 X141.385 Y150.252
G1 X141.251 Y150.119
G1 X140.749 Y149.617 E.02115
G1 X140.615 Y149.483
G1 X140.615 Y150.016
G1 X140.749 Y150.15
G1 X141.251 Y150.652 E.02115
G1 X141.385 Y150.786
G1 X141.385 Y151.319
G1 X141.251 Y151.185
G1 X140.749 Y150.683 E.02115
G1 X140.615 Y150.549
G1 X140.615 Y151.083
G1 X140.749 Y151.216
G1 X141.251 Y151.718 E.02115
G1 X141.385 Y151.852
G1 X141.385 Y152.385
G1 X141.251 Y152.252
G1 X140.749 Y151.75 E.02115
G1 X140.615 Y151.616
G1 X140.615 Y152.149
G1 X140.749 Y152.283
G1 X141.251 Y152.785 E.02115
G1 X141.385 Y152.919
G1 X141.385 Y153.452
G1 X141.251 Y153.318
G1 X140.749 Y152.816 E.02115
G1 X140.615 Y152.682
G1 X140.615 Y153.216
G1 X140.749 Y153.349
G1 X141.251 Y153.851 E.02115
G1 X141.385 Y153.985
G1 X141.385 Y154.518
G1 X141.251 Y154.385
G1 X140.749 Y153.883 E.02115
G1 X140.615 Y153.749
G1 X140.615 Y154.282
G1 X140.749 Y154.416
G1 X141.251 Y154.918 E.02115
G1 X141.385 Y155.052
G1 X141.385 Y155.585
G1 X141.251 Y155.451
G1 X140.749 Y154.949 E.02115
G1 X140.615 Y154.816
G1 X140.615 Y155.349
G1 X140.749 Y155.482
G1 X141.251 Y155.984 E.02115
G1 X141.385 Y156.118
G1 X141.385 Y156.651
G1 X141.251 Y156.518
G1 X140.749 Y156.016 E.02115
G1 X140.615 Y155.882
G1 X140.615 Y156.415
G1 X140.749 Y156.549
G1 X141.251 Y157.051 E.02115
G1 X141.385 Y157.185
G1 X141.385 Y157.718
G1 X141.251 Y157.584
G1 X140.749 Y157.082 E.02115
G1 X140.615 Y156.949
G1 X140.615 Y157.482
G1 X140.749 Y157.615
G1 X141.251 Y158.118 E.02115
G1 X141.385 Y158.251
G1 X141.385 Y158.784
G1 X141.251 Y158.651
G1 X140.749 Y158.149 E.02115
G1 X140.615 Y158.015
G1 X140.615 Y158.548
G1 X140.749 Y158.682
G1 X141.251 Y159.184 E.02115
G1 X141.385 Y159.318
G1 X141.385 Y159.851
G1 X141.251 Y159.717
G1 X140.749 Y159.215 E.02115
G1 X140.615 Y159.082
G1 X140.615 Y159.615
G1 X140.749 Y159.748
G1 X141.251 Y160.251 E.02115
G1 X141.385 Y160.384
G1 X141.385 Y160.917
G1 X141.251 Y160.784
G1 X140.749 Y160.282 E.02115
G1 X140.615 Y160.148
G1 X140.615 Y160.681
G1 X140.749 Y160.815
G1 X141.251 Y161.317 E.02115
G1 X141.385 Y161.451
G1 X141.385 Y161.984
G1 X141.251 Y161.85
G1 X140.749 Y161.348 E.02115
G1 X140.615 Y161.215
G1 X140.615 Y161.748
G1 X140.749 Y161.881
G1 X141.251 Y162.384 E.02115
G1 X141.385 Y162.517
G1 X141.385 Y163.05
G1 X141.251 Y162.917
G1 X140.749 Y162.415 E.02115
G1 X140.615 Y162.281
G1 X140.615 Y162.814
G1 X140.749 Y162.948
G1 X141.251 Y163.45 E.02115
G1 X141.385 Y163.584
G1 X141.385 Y164.117
G1 X141.251 Y163.983
G1 X140.749 Y163.481 E.02115
G1 X140.615 Y163.348
G1 X140.615 Y163.881
G1 X140.749 Y164.015
G1 X141.251 Y164.517 E.02115
G1 X141.385 Y164.65
G1 X141.385 Y165.183
G1 X141.251 Y165.05
G1 X140.749 Y164.548 E.02115
G1 X140.615 Y164.414
G1 X140.615 Y164.947
G1 X140.749 Y165.081
G1 X141.251 Y165.583 E.02115
G1 X141.385 Y165.717
G1 X141.385 Y166.25
G1 X141.251 Y166.116
G1 X140.749 Y165.614 E.02115
G1 X140.615 Y165.481
G1 X140.615 Y166.014
G1 X140.749 Y166.148
G1 X141.251 Y166.65 E.02115
G1 X141.385 Y166.783
G1 X141.385 Y167.317
G1 X141.251 Y167.183
G1 X140.749 Y166.681 E.02115
G1 X140.615 Y166.547
G1 X140.615 Y167.08
G1 X140.749 Y167.214
G1 X141.251 Y167.716 E.02115
G1 X141.385 Y167.85
G1 X141.385 Y168.383
G1 X141.251 Y168.249
G1 X140.749 Y167.747 E.02115
G1 X140.615 Y167.614
G1 X140.615 Y168.147
G1 X140.749 Y168.281
G1 X141.251 Y168.783 E.02115
G1 X141.385 Y168.916
G1 X141.385 Y169.45
G1 X141.251 Y169.316
G1 X140.749 Y168.814 E.02115
G1 X140.615 Y168.68
G1 X140.615 Y169.213
G1 X140.749 Y169.347
G1 X141.251 Y169.849 E.02115
G1 X141.385 Y169.983
G1 X141.385 Y170.516
G1 X141.251 Y170.382
G1 X140.749 Y169.88 E.02115
G1 X140.615 Y169.747
G1 X140.615 Y170.28
G1 X140.749 Y170.414
G1 X141.251 Y170.916 E.02115
G1 X141.385 Y171.049
G1 X141.385 Y171.583
G1 X141.251 Y171.449
G1 X140.749 Y170.947 E.02115
G1 X140.615 Y170.813
G1 X140.615 Y171.346
G1 X140.749 Y171.48
G1 X141.251 Y171.982 E.02115
G1 X141.385 Y172.116
G1 X141.385 Y172.649
G1 X141.251 Y172.515
G1 X140.749 Y172.013 E.02115
G1 X140.615 Y171.88
G1 X140.615 Y172.413
G1 X140.749 Y172.547
G1 X141.251 Y173.049 E.02115
G1 X141.385 Y173.182
G1 X141.385 Y173.716
G1 X141.251 Y173.582
G1 X140.749 Y173.08 E.02115
G1 X140.615 Y172.946
G1 X140.615 Y173.48
G1 X140.749 Y173.613
G1 X141.251 Y174.115 E.02115
G1 X141.385 Y174.249
G1 X141.385 Y174.782
G1 X141.251 Y174.648
G1 X140.749 Y174.146 E.02115
G1 X140.615 Y174.013
G1 X141.72 Y174.584
G1 X141.853 Y174.717
G1 X142.471 Y175.335 E.02602
G1 X142.605 Y175.469
G1 X142.38 Y175.777
M73 P72 R4
G1 X142.246 Y175.644
G1 X141.32 Y174.717 E.03902
G1 X141.186 Y174.584
G1 X140.615 Y174.546
G1 X140.749 Y174.68
G1 X141.713 Y175.644 E.04061
G1 X141.847 Y175.777
G1 X141.313 Y175.777
G1 X141.18 Y175.644
G1 X140.253 Y174.717 E.03902
G1 X140.12 Y174.584
G1 X139.587 Y174.584
G1 X139.72 Y174.717
G1 X140.647 Y175.644 E.03902
G1 X140.78 Y175.777
G1 X140.247 Y175.777
G1 X140.113 Y175.644
G1 X139.529 Y175.06 E.02461
M204 S10000
G1 X139.518 Y175.782 F60000
; FEATURE: Gap infill
; LINE_WIDTH: 0.26667
G1 F15000
M204 S8000
G1 X142.482 Y175.782 E.0524
; WIPE_START
G1 X141.482 Y175.782 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I0 J1.217 P1  F60000
G1 X153.518 Y175.782 Z3
G1 Z2.6
G1 E.4 F1800
G1 F15000
M204 S8000
G1 X156.482 Y175.782 E.0524
; WIPE_START
G1 X155.482 Y175.782 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I1.216 J.036 P1  F60000
G1 X157.252 Y116.527 Z3
G1 Z2.6
G1 E.4 F1800
; FEATURE: Top surface
; LINE_WIDTH: 0.42
G1 F12000
M204 S2000
G1 X156.482 Y115.756 E.03247
G1 X156.348 Y115.623
G1 X155.815 Y115.623
G1 X155.948 Y115.756
G1 X156.875 Y116.683 E.03902
G1 X157.008 Y116.816
G1 X156.475 Y116.816
G1 X156.341 Y116.683
G1 X155.415 Y115.756 E.03902
G1 X155.281 Y115.623
G1 X154.748 Y115.623
G1 X154.882 Y115.756
G1 X155.808 Y116.683 E.03902
G1 X155.942 Y116.816
G1 X155.409 Y116.816
G1 X155.275 Y116.683
G1 X154.349 Y115.756 E.03902
G1 X154.215 Y115.623
G1 X153.682 Y115.623
G1 X153.815 Y115.756
G1 X154.742 Y116.683 E.03902
G1 X154.875 Y116.816
G1 X154.342 Y116.816
G1 X154.208 Y116.683
G1 X153.282 Y115.756 E.03902
G1 X153.148 Y115.623
G1 X152.659 Y115.667
G1 X152.793 Y115.8
G1 X153.675 Y116.683 E.03716
G1 X153.809 Y116.816
G1 X153.276 Y116.816
G1 X153.142 Y116.683
G1 X152.748 Y116.288 E.01661
; WIPE_START
M204 S8000
G1 X153.142 Y116.683 E-.21184
G1 X153.276 Y116.816 E-.07182
G1 X153.529 Y116.816 E-.09634
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I-.259 J1.189 P1  F60000
G1 X155.251 Y117.192 Z3
G1 Z2.6
G1 E.4 F1800
G1 F12000
M204 S2000
G1 X154.749 Y116.69 E.02115
G1 X154.615 Y116.556
G1 X154.615 Y117.09
G1 X154.749 Y117.223
G1 X155.251 Y117.725 E.02115
G1 X155.385 Y117.859
G1 X155.385 Y118.392
G1 X155.251 Y118.258
G1 X154.749 Y117.756 E.02115
G1 X154.615 Y117.623
G1 X154.615 Y118.156
G1 X154.749 Y118.29
G1 X155.251 Y118.792 E.02115
G1 X155.385 Y118.925
G1 X155.385 Y119.459
G1 X155.251 Y119.325
G1 X154.749 Y118.823 E.02115
G1 X154.615 Y118.689
G1 X154.615 Y119.223
G1 X154.749 Y119.356
G1 X155.251 Y119.858 E.02115
G1 X155.385 Y119.992
G1 X155.385 Y120.525
G1 X155.251 Y120.392
G1 X154.749 Y119.889 E.02115
G1 X154.615 Y119.756
G1 X154.615 Y120.289
G1 X154.749 Y120.423
G1 X155.251 Y120.925 E.02115
G1 X155.385 Y121.058
G1 X155.385 Y121.592
G1 X155.251 Y121.458
G1 X154.749 Y120.956 E.02115
G1 X154.615 Y120.822
G1 X154.615 Y121.356
G1 X154.749 Y121.489
G1 X155.251 Y121.991 E.02115
G1 X155.385 Y122.125
G1 X155.385 Y122.658
G1 X155.251 Y122.525
G1 X154.749 Y122.022 E.02115
G1 X154.615 Y121.889
G1 X154.615 Y122.422
G1 X154.749 Y122.556
G1 X155.251 Y123.058 E.02115
G1 X155.385 Y123.191
G1 X155.385 Y123.725
G1 X155.251 Y123.591
G1 X154.749 Y123.089 E.02115
G1 X154.615 Y122.955
G1 X154.615 Y123.489
G1 X154.749 Y123.622
G1 X155.251 Y124.124 E.02115
G1 X155.385 Y124.258
G1 X155.385 Y124.791
G1 X155.251 Y124.658
G1 X154.749 Y124.156 E.02115
G1 X154.615 Y124.022
G1 X154.615 Y124.555
G1 X154.749 Y124.689
G1 X155.251 Y125.191 E.02115
G1 X155.385 Y125.324
G1 X155.385 Y125.858
G1 X155.251 Y125.724
G1 X154.749 Y125.222 E.02115
G1 X154.615 Y125.088
G1 X154.615 Y125.622
G1 X154.749 Y125.755
G1 X155.251 Y126.257 E.02115
G1 X155.385 Y126.391
G1 X155.385 Y126.924
G1 X155.251 Y126.791
G1 X154.749 Y126.289 E.02115
G1 X154.615 Y126.155
G1 X154.615 Y126.688
G1 X154.749 Y126.822
G1 X155.251 Y127.324 E.02115
G1 X155.385 Y127.458
G1 X155.385 Y127.991
G1 X155.251 Y127.857
G1 X154.749 Y127.355 E.02115
G1 X154.615 Y127.221
G1 X154.615 Y127.755
G1 X154.749 Y127.888
G1 X155.251 Y128.39 E.02115
G1 X155.385 Y128.524
G1 X155.385 Y129.057
G1 X155.251 Y128.924
G1 X154.749 Y128.422 E.02115
G1 X154.615 Y128.288
G1 X154.615 Y128.821
G1 X154.749 Y128.955
G1 X155.251 Y129.457 E.02115
G1 X155.385 Y129.591
G1 X155.385 Y130.124
G1 X155.251 Y129.99
G1 X154.749 Y129.488 E.02115
G1 X154.615 Y129.354
G1 X154.615 Y129.888
G1 X154.749 Y130.021
G1 X155.251 Y130.523 E.02115
G1 X155.385 Y130.657
G1 X155.385 Y131.19
G1 X155.251 Y131.057
G1 X154.749 Y130.555 E.02115
G1 X154.615 Y130.421
G1 X154.615 Y130.954
G1 X154.749 Y131.088
G1 X155.251 Y131.59 E.02115
G1 X155.385 Y131.724
G1 X155.385 Y132.257
G1 X155.251 Y132.123
G1 X154.749 Y131.621 E.02115
G1 X154.615 Y131.487
G1 X154.615 Y132.021
G1 X154.749 Y132.154
G1 X155.251 Y132.656 E.02115
G1 X155.385 Y132.79
G1 X155.385 Y133.323
G1 X155.251 Y133.19
G1 X154.749 Y132.688 E.02115
G1 X154.615 Y132.554
G1 X154.615 Y133.087
G1 X154.749 Y133.221
G1 X155.251 Y133.723 E.02115
G1 X155.385 Y133.857
G1 X155.385 Y134.39
G1 X155.251 Y134.256
G1 X154.749 Y133.754 E.02115
G1 X154.615 Y133.621
G1 X154.615 Y134.154
G1 X154.749 Y134.287
G1 X155.251 Y134.789 E.02115
G1 X155.385 Y134.923
G1 X155.385 Y135.456
G1 X155.251 Y135.323
G1 X154.749 Y134.821 E.02115
G1 X154.615 Y134.687
G1 X154.615 Y135.22
G1 X154.749 Y135.354
G1 X155.251 Y135.856 E.02115
G1 X155.385 Y135.99
G1 X155.385 Y136.523
G1 X155.251 Y136.389
G1 X154.749 Y135.887 E.02115
G1 X154.615 Y135.754
G1 X154.615 Y136.287
G1 X154.749 Y136.42
G1 X155.251 Y136.923 E.02115
G1 X155.385 Y137.056
G1 X155.385 Y137.589
G1 X155.251 Y137.456
G1 X154.749 Y136.954 E.02115
G1 X154.615 Y136.82
G1 X154.615 Y137.353
G1 X154.749 Y137.487
G1 X155.251 Y137.989 E.02115
G1 X155.385 Y138.123
G1 X155.385 Y138.656
G1 X155.251 Y138.522
G1 X154.749 Y138.02 E.02115
G1 X154.615 Y137.887
G1 X154.615 Y138.42
G1 X154.749 Y138.553
G1 X155.251 Y139.056 E.02115
G1 X155.385 Y139.189
G1 X155.385 Y139.722
G1 X155.251 Y139.589
G1 X154.749 Y139.087 E.02115
G1 X154.615 Y138.953
G1 X154.615 Y139.486
G1 X154.749 Y139.62
G1 X155.251 Y140.122 E.02115
G1 X155.385 Y140.256
G1 X155.385 Y140.789
G1 X155.251 Y140.655
G1 X154.749 Y140.153 E.02115
G1 X154.615 Y140.02
G1 X154.615 Y140.553
G1 X154.749 Y140.687
G1 X155.251 Y141.189 E.02115
G1 X155.385 Y141.322
G1 X155.385 Y141.855
G1 X155.251 Y141.722
G1 X154.749 Y141.22 E.02115
G1 X154.615 Y141.086
G1 X154.615 Y141.619
G1 X154.749 Y141.753
G1 X155.251 Y142.255 E.02115
G1 X155.385 Y142.389
G1 X155.385 Y142.922
G1 X155.251 Y142.788
G1 X154.749 Y142.286 E.02115
G1 X154.615 Y142.153
G1 X154.615 Y142.686
G1 X154.749 Y142.82
G1 X155.251 Y143.322 E.02115
G1 X155.385 Y143.455
G1 X155.385 Y143.988
G1 X155.251 Y143.855
G1 X154.749 Y143.353 E.02115
G1 X154.615 Y143.219
G1 X154.615 Y143.752
G1 X154.749 Y143.886
G1 X155.251 Y144.388 E.02115
G1 X155.385 Y144.522
G1 X155.385 Y145.055
G1 X155.251 Y144.921
G1 X154.749 Y144.419 E.02115
G1 X154.615 Y144.286
G1 X154.615 Y144.819
G1 X154.749 Y144.953
G1 X155.251 Y145.455 E.02115
G1 X155.385 Y145.588
G1 X155.385 Y146.122
G1 X155.251 Y145.988
G1 X154.749 Y145.486 E.02115
G1 X154.615 Y145.352
G1 X154.615 Y145.885
G1 X154.749 Y146.019
G1 X155.251 Y146.521 E.02115
G1 X155.385 Y146.655
G1 X155.385 Y147.188
G1 X155.251 Y147.054
G1 X154.749 Y146.552 E.02115
G1 X154.615 Y146.419
G1 X154.615 Y146.952
G1 X154.749 Y147.086
G1 X155.251 Y147.588 E.02115
G1 X155.385 Y147.721
G1 X155.385 Y148.255
G1 X155.251 Y148.121
G1 X154.749 Y147.619 E.02115
G1 X154.615 Y147.485
G1 X154.615 Y148.018
G1 X154.749 Y148.152
G1 X155.251 Y148.654 E.02115
G1 X155.385 Y148.788
G1 X155.385 Y149.321
G1 X155.251 Y149.187
G1 X154.749 Y148.685 E.02115
G1 X154.615 Y148.552
G1 X154.615 Y149.085
G1 X154.749 Y149.219
G1 X155.251 Y149.721 E.02115
G1 X155.385 Y149.854
G1 X155.385 Y150.388
G1 X155.251 Y150.254
G1 X154.749 Y149.752 E.02115
G1 X154.615 Y149.618
G1 X154.615 Y150.151
G1 X154.749 Y150.285
G1 X155.251 Y150.787 E.02115
G1 X155.385 Y150.921
G1 X155.385 Y151.454
G1 X155.251 Y151.32
G1 X154.749 Y150.818 E.02115
G1 X154.615 Y150.685
G1 X154.615 Y151.218
G1 X154.749 Y151.352
G1 X155.251 Y151.854 E.02115
G1 X155.385 Y151.987
G1 X155.385 Y152.521
G1 X155.251 Y152.387
G1 X154.749 Y151.885 E.02115
G1 X154.615 Y151.751
G1 X154.615 Y152.285
G1 X154.749 Y152.418
G1 X155.251 Y152.92 E.02115
G1 X155.385 Y153.054
G1 X155.385 Y153.587
G1 X155.251 Y153.453
G1 X154.749 Y152.951 E.02115
G1 X154.615 Y152.818
G1 X154.615 Y153.351
G1 X154.749 Y153.485
G1 X155.251 Y153.987 E.02115
G1 X155.385 Y154.12
G1 X155.385 Y154.654
G1 X155.251 Y154.52
G1 X154.749 Y154.018 E.02115
G1 X154.615 Y153.884
G1 X154.615 Y154.418
G1 X154.749 Y154.551
G1 X155.251 Y155.053 E.02115
G1 X155.385 Y155.187
G1 X155.385 Y155.72
G1 X155.251 Y155.587
G1 X154.749 Y155.084 E.02115
G1 X154.615 Y154.951
G1 X154.615 Y155.484
G1 X154.749 Y155.618
G1 X155.251 Y156.12 E.02115
G1 X155.385 Y156.253
G1 X155.385 Y156.787
G1 X155.251 Y156.653
G1 X154.749 Y156.151 E.02115
G1 X154.615 Y156.017
G1 X154.615 Y156.551
G1 X154.749 Y156.684
G1 X155.251 Y157.186 E.02115
G1 X155.385 Y157.32
G1 X155.385 Y157.853
G1 X155.251 Y157.72
G1 X154.749 Y157.217 E.02115
G1 X154.615 Y157.084
G1 X154.615 Y157.617
G1 X154.749 Y157.751
G1 X155.251 Y158.253 E.02115
G1 X155.385 Y158.386
G1 X155.385 Y158.92
G1 X155.251 Y158.786
G1 X154.749 Y158.284 E.02115
G1 X154.615 Y158.15
G1 X154.615 Y158.684
G1 X154.749 Y158.817
G1 X155.251 Y159.319 E.02115
G1 X155.385 Y159.453
G1 X155.385 Y159.986
G1 X155.251 Y159.853
G1 X154.749 Y159.351 E.02115
G1 X154.615 Y159.217
G1 X154.615 Y159.75
G1 X154.749 Y159.884
G1 X155.251 Y160.386 E.02115
G1 X155.385 Y160.519
G1 X155.385 Y161.053
G1 X155.251 Y160.919
G1 X154.749 Y160.417 E.02115
G1 X154.615 Y160.283
G1 X154.615 Y160.817
G1 X154.749 Y160.95
G1 X155.251 Y161.452 E.02115
G1 X155.385 Y161.586
G1 X155.385 Y162.119
G1 X155.251 Y161.986
G1 X154.749 Y161.484 E.02115
G1 X154.615 Y161.35
G1 X154.615 Y161.883
G1 X154.749 Y162.017
G1 X155.251 Y162.519 E.02115
G1 X155.385 Y162.653
G1 X155.385 Y163.186
G1 X155.251 Y163.052
G1 X154.749 Y162.55 E.02115
G1 X154.615 Y162.416
G1 X154.615 Y162.95
G1 X154.749 Y163.083
G1 X155.251 Y163.585 E.02115
G1 X155.385 Y163.719
G1 X155.385 Y164.252
G1 X155.251 Y164.119
G1 X154.749 Y163.617 E.02115
G1 X154.615 Y163.483
G1 X154.615 Y164.016
G1 X154.749 Y164.15
G1 X155.251 Y164.652 E.02115
G1 X155.385 Y164.786
G1 X155.385 Y165.319
G1 X155.251 Y165.185
G1 X154.749 Y164.683 E.02115
G1 X154.615 Y164.549
G1 X154.615 Y165.083
G1 X154.749 Y165.216
G1 X155.251 Y165.718 E.02115
G1 X155.385 Y165.852
G1 X155.385 Y166.385
G1 X155.251 Y166.252
G1 X154.749 Y165.75 E.02115
G1 X154.615 Y165.616
G1 X154.615 Y166.149
G1 X154.749 Y166.283
G1 X155.251 Y166.785 E.02115
G1 X155.385 Y166.919
G1 X155.385 Y167.452
G1 X155.251 Y167.318
G1 X154.749 Y166.816 E.02115
G1 X154.615 Y166.682
G1 X154.615 Y167.216
G1 X154.749 Y167.349
G1 X155.251 Y167.851 E.02115
G1 X155.385 Y167.985
G1 X155.385 Y168.518
G1 X155.251 Y168.385
G1 X154.749 Y167.883 E.02115
G1 X154.615 Y167.749
G1 X154.615 Y168.282
G1 X154.749 Y168.416
G1 X155.251 Y168.918 E.02115
G1 X155.385 Y169.052
G1 X155.385 Y169.585
G1 X155.251 Y169.451
G1 X154.749 Y168.949 E.02115
G1 X154.615 Y168.816
G1 X154.615 Y169.349
G1 X154.749 Y169.482
G1 X155.251 Y169.984 E.02115
G1 X155.385 Y170.118
G1 X155.385 Y170.651
G1 X155.251 Y170.518
G1 X154.749 Y170.016 E.02115
G1 X154.615 Y169.882
G1 X154.615 Y170.415
G1 X154.749 Y170.549
G1 X155.251 Y171.051 E.02115
G1 X155.385 Y171.185
G1 X155.385 Y171.718
G1 X155.251 Y171.584
G1 X154.749 Y171.082 E.02115
G1 X154.615 Y170.949
G1 X154.615 Y171.482
G1 X154.749 Y171.615
G1 X155.251 Y172.117 E.02115
G1 X155.385 Y172.251
G1 X155.385 Y172.784
G1 X155.251 Y172.651
G1 X154.749 Y172.149 E.02115
G1 X154.615 Y172.015
G1 X154.615 Y172.548
G1 X154.749 Y172.682
G1 X155.251 Y173.184 E.02115
G1 X155.385 Y173.318
G1 X155.385 Y173.851
G1 X155.251 Y173.717
G1 X154.749 Y173.215 E.02115
G1 X154.615 Y173.082
G1 X154.615 Y173.615
G1 X154.749 Y173.748
G1 X155.251 Y174.251 E.02115
G1 X155.718 Y174.717
G1 X156.471 Y175.47 E.03172
G1 X156.605 Y175.604
G1 X156.245 Y175.777
G1 X156.111 Y175.644
G1 X154.749 Y174.282 E.05738
G1 X154.615 Y174.148
G1 X154.518 Y174.584
G1 X154.651 Y174.717
G1 X155.578 Y175.644 E.03902
G1 X155.711 Y175.777
G1 X155.178 Y175.777
G1 X155.044 Y175.644
G1 X154.118 Y174.717 E.03902
G1 X153.984 Y174.584
G1 X153.451 Y174.584
G1 X153.585 Y174.717
G1 X154.511 Y175.644 E.03902
G1 X154.645 Y175.777
G1 X154.112 Y175.777
G1 X153.978 Y175.644
G1 X153.529 Y175.195 E.01891
; WIPE_START
M204 S8000
G1 X153.978 Y175.644 E-.24122
G1 X154.112 Y175.777 E-.07182
G1 X154.288 Y175.777 E-.06696
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I1.216 J.057 P1  F60000
G1 X157.181 Y114.118 Z3
G1 Z2.6
G1 E.4 F1800
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.432559
G1 F12000
M204 S8000
G1 X157.181 Y113.919 E.00613
G1 X137.508 Y113.919 E.60553
G2 X136.584 Y113.908 I-.729 J23.39 E.02843
G1 X136.584 Y115.292 E.04258
G1 X137.319 Y115.292 E.02262
G1 X137.319 Y114.516 E.02387
G1 X137.333 Y114.445 E.00224
G1 X137.508 Y114.317 E.00665
G1 X144.492 Y114.317 E.21499
G1 X144.681 Y114.516 E.00844
G1 X144.681 Y115.292 E.02387
G1 X151.319 Y115.292 E.20431
G1 X151.319 Y114.516 E.02387
G1 X151.508 Y114.317 E.00844
G1 X157.181 Y114.317 E.17463
G1 X157.181 Y114.178 E.00428
; WIPE_START
G1 X157.181 Y114.317 E-.05285
G1 X156.32 Y114.317 E-.32715
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I-.007 J-1.217 P1  F60000
G1 X151.02 Y114.348 Z3
G1 Z2.6
G1 E.4 F1800
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X144.953 Y114.348 E.24113
G1 X145.121 Y114.516 E.00943
G1 X145.121 Y114.852 E.01334
G1 X150.879 Y114.852 E.22887
G1 X150.879 Y114.516 E.01334
G1 X150.981 Y114.394 E.00632
; WIPE_START
G1 X150.879 Y114.516 E-.06041
G1 X150.879 Y114.852 E-.1275
G1 X150.373 Y114.852 E-.1921
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I-.007 J-1.217 P1  F60000
G1 X136.952 Y114.924 Z3
G1 Z2.6
M73 P73 R4
G1 E.4 F1800
; LINE_WIDTH: 0.42236
G1 F12000
M204 S8000
G1 X136.971 Y114.357 E.017
; WIPE_START
G1 X136.952 Y114.924 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I-.408 J-1.146 P1  F60000
G1 X135.796 Y115.336 Z3
G1 Z2.6
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X134.722 Y115.336 E.03452
G1 X135.117 Y113.864 E.04897
G1 X134.611 Y113.864 E.01627
G1 X136.082 Y115.336 E.0669
G1 X136 Y115.336 E.00264
G1 X136.192 Y114.548 E.02606
G1 X133.255 Y115.336 E.09779
G1 X133.445 Y115.336 E.00614
G1 X133.84 Y113.864 E.04897
G1 X133.979 Y113.864 E.00447
G1 X128.337 Y115.336 E.18748
G1 X128.731 Y113.864 E.04897
; WIPE_START
G1 X128.472 Y114.83 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I-.76 J.95 P1  F60000
G1 X129.103 Y115.336 Z3
G1 Z2.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X127.632 Y113.864 E.0669
G1 X127.454 Y113.864 E.00573
G1 X127.06 Y115.336 E.04897
G1 X127.359 Y115.336 E.00962
G1 X125.888 Y113.864 E.0669
G1 X126.177 Y113.864 E.0093
G1 X125.783 Y115.336 E.04897
G1 X125.614 Y115.336 E.00542
G1 X124.143 Y113.864 E.0669
G1 X124.446 Y113.864 E.00974
G1 X121.443 Y114.654 E.09984
G1 X122.125 Y115.336 E.03101
G1 X121.952 Y115.336 E.00559
G1 X122.346 Y113.864 E.04897
G1 X122.399 Y113.864 E.00171
G1 X123.87 Y115.336 E.0669
G1 X123.722 Y115.336 E.00475
G1 X129.212 Y113.864 E.18277
G1 X129.377 Y113.864 E.00529
G1 X130.891 Y115.336 E.06789
G1 X131.285 Y113.864 E.04897
G1 X131.121 Y113.864 E.00527
G1 X132.593 Y115.336 E.0669
G1 X132.168 Y115.336 E.01364
G1 X132.562 Y113.864 E.04897
G1 X131.489 Y113.864 E.03452
M204 S10000
G1 X130.918 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X130.008 Y113.864 E.02925
G1 X129.614 Y115.336 E.04897
; WIPE_START
G1 X129.873 Y114.37 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I.203 J1.2 P1  F60000
G1 X132.866 Y113.864 Z3
G1 Z2.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X134.337 Y115.336 E.0669
; WIPE_START
G1 X133.63 Y114.628 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I.116 J-1.211 P1  F60000
G1 X125.684 Y113.864 Z3
G1 Z2.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X124.9 Y113.864 E.02522
G1 X124.506 Y115.336 E.04897
; WIPE_START
G1 X124.765 Y114.37 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I.492 J-1.113 P1  F60000
G1 X123.623 Y113.864 Z3
G1 Z2.6
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X123.229 Y115.336 E.04897
G1 X122.329 Y115.336 E.02893
; WIPE_START
G1 X123.229 Y115.336 E-.34193
G1 X123.255 Y115.239 E-.03807
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3 I-.029 J-1.217 P1  F60000
G1 X121.052 Y115.292 Z3
G1 Z2.6
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X121.052 Y113.908 E.04121
G1 X112.808 Y113.908 E.24553
G1 X112.808 Y115.292 E.04121
G1 X120.992 Y115.292 E.24375
M204 S10000
G1 X120.611 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X120.611 Y114.348 E.02
G1 X113.248 Y114.348 E.29267
G1 X113.248 Y114.852 E.02
G1 X120.551 Y114.852 E.29029
; CHANGE_LAYER
; Z_HEIGHT: 2.8
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F10731.32
G1 X119.551 Y114.852 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 14/27
; update layer progress
M73 L14
M991 S0 P13 ;notify layer change
M106 S71.4
; OBJECT_ID: 16
; COOLING_NODE: 0
; start printing object, unique label id: 16
M624 BAAAAAAAAAA=
M204 S10000
G17
G3 Z3 I-.782 J.933 P1  F60000
G1 X195.345 Y178.394 Z3
G1 Z2.8
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X195.256 Y178.406 E.00289
G3 X194.575 Y171.609 I-.256 J-3.407 E.33971
G1 X194.915 Y171.583 E.01097
G3 X195.76 Y178.33 I.085 J3.416 E.32324
G1 X195.404 Y178.385 E.01158
; COOLING_NODE: 0
M204 S10000
G1 X195.285 Y177.992 F60000
G1 F13265.217
M204 S8000
G1 X195.225 Y178 E.00196
G3 X194.625 Y172.013 I-.225 J-3.001 E.29921
G1 X194.925 Y171.991 E.00966
G3 X195.669 Y177.933 I.075 J3.009 E.28471
G1 X195.345 Y177.983 E.01056
; COOLING_NODE: 0
M204 S10000
G1 X195.226 Y177.59 F60000
G1 F13265.217
M204 S8000
G1 X195.195 Y177.594 E.00102
G3 X194.676 Y172.417 I-.195 J-2.595 E.25871
G1 X194.935 Y172.398 E.00835
G3 X195.579 Y177.536 I.065 J2.601 E.24617
G1 X195.285 Y177.581 E.00955
; COOLING_NODE: 0
M204 S250
G1 X195.168 Y177.203 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X195.165 Y177.203 E.00009
G3 X194.725 Y172.807 I-.165 J-2.204 E.20352
G1 X194.945 Y172.79 E.00657
G3 X195.492 Y177.154 I.055 J2.209 E.19365
G1 X195.228 Y177.194 E.00796
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X195.165 Y177.203 E-.02392
G1 X194.835 Y177.204 E-.1255
G1 X194.399 Y177.127 E-.16834
G1 X194.246 Y177.067 E-.06225
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.2 I-1.086 J.549 P1  F60000
G1 X201.584 Y191.584 Z3.2
G1 Z2.8
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y191.584 E.42342
G1 X188.416 Y170.416 E.68067
G1 X201.584 Y170.416 E.42342
G1 X201.584 Y191.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y191.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y191.991 E.4496
G1 X188.009 Y170.009 E.70685
G1 X201.991 Y170.009 E.4496
G1 X201.991 Y191.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y192.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y192.398 E.47578
G1 X187.602 Y169.602 E.73303
G1 X202.398 Y169.602 E.47578
G1 X202.398 Y192.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y192.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y192.79 E.46408
G1 X187.21 Y169.21 E.70237
G1 X202.79 Y169.21 E.46408
G1 X202.79 Y192.73 E.70058
; object ids of layer 14 start: 8,12,16
M624 BwAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer14 end: 8,12,16
M625
; WIPE_START
M204 S8000
G1 X201.79 Y192.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.2 I.921 J-.796 P1  F60000
G1 X200.654 Y191.42 Z3.2
G1 Z2.8
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42179
G1 F14252.909
M204 S8000
G1 X201.251 Y190.824 E.02524
G1 X201.251 Y190.288 E.01604
G1 X200.288 Y191.251 E.04074
G1 X199.752 Y191.251 E.01604
G1 X201.251 Y189.752 E.06342
G1 X201.251 Y189.216 E.01604
G1 X199.216 Y191.251 E.08609
G1 X198.681 Y191.251 E.01604
G1 X201.251 Y188.681 E.10877
G1 X201.251 Y188.145 E.01604
G1 X198.145 Y191.251 E.13145
G1 X197.609 Y191.251 E.01604
G1 X201.251 Y187.609 E.15413
G1 X201.251 Y187.073 E.01604
G1 X197.073 Y191.251 E.1768
G1 X196.537 Y191.251 E.01604
G1 X201.251 Y186.537 E.19948
G1 X201.251 Y186.002 E.01604
G1 X196.002 Y191.251 E.22216
G1 X195.466 Y191.251 E.01604
G1 X201.251 Y185.466 E.24484
G1 X201.251 Y184.93 E.01604
G1 X194.93 Y191.251 E.26751
G1 X194.394 Y191.251 E.01604
G1 X201.251 Y184.394 E.29019
G1 X201.251 Y183.858 E.01604
G1 X193.858 Y191.251 E.31287
G1 X193.323 Y191.251 E.01604
G1 X201.251 Y183.323 E.33555
G1 X201.251 Y182.787 E.01604
G1 X192.787 Y191.251 E.35823
G1 X192.251 Y191.251 E.01604
G1 X201.251 Y182.251 E.3809
G1 X201.251 Y181.715 E.01604
G1 X191.715 Y191.251 E.40358
G1 X191.179 Y191.251 E.01604
G1 X201.251 Y181.179 E.42626
G1 X201.251 Y180.644 E.01604
G1 X190.644 Y191.251 E.44894
G1 X190.108 Y191.251 E.01604
G1 X201.251 Y180.108 E.47161
G1 X201.251 Y179.572 E.01604
G1 X189.572 Y191.251 E.49429
G1 X189.036 Y191.251 E.01604
G1 X201.251 Y179.036 E.51697
G1 X201.251 Y178.5 E.01604
G1 X188.749 Y191.001 E.5291
G1 X188.749 Y190.466 E.01604
G1 X201.251 Y177.965 E.5291
G1 X201.251 Y177.429 E.01604
G1 X188.749 Y189.93 E.5291
G1 X188.749 Y189.394 E.01604
G1 X201.251 Y176.893 E.5291
G1 X201.251 Y176.357 E.01604
G1 X188.749 Y188.858 E.5291
G1 X188.749 Y188.322 E.01604
G1 X201.251 Y175.821 E.5291
G1 X201.251 Y175.286 E.01604
G1 X188.749 Y187.787 E.5291
G1 X188.749 Y187.251 E.01604
G1 X201.251 Y174.75 E.5291
G1 X201.251 Y174.214 E.01604
G1 X188.749 Y186.715 E.5291
G1 X188.749 Y186.179 E.01604
G1 X196.49 Y178.438 E.32762
G3 X195.714 Y178.679 I-1.521 J-3.538 E.02437
G1 X188.749 Y185.643 E.29477
G1 X188.749 Y185.108 E.01604
G1 X195.11 Y178.747 E.26919
G3 X194.596 Y178.726 I-.066 J-4.501 E.0154
G1 X188.749 Y184.572 E.24744
G1 X188.749 Y184.036 E.01604
G1 X194.14 Y178.645 E.22816
G3 X193.725 Y178.525 I.396 J-2.134 E.01296
G1 X188.749 Y183.5 E.21059
G1 X188.749 Y182.964 E.01604
G1 X193.348 Y178.366 E.19465
G3 X193.004 Y178.174 I.785 J-1.82 E.01181
G1 X188.749 Y182.429 E.18007
G1 X188.749 Y181.893 E.01604
G1 X192.689 Y177.953 E.16674
G3 X192.402 Y177.705 I1.097 J-1.557 E.01139
G1 X188.749 Y181.357 E.15459
G1 X188.749 Y180.821 E.01604
G1 X192.143 Y177.427 E.14364
G3 X191.909 Y177.125 I1.392 J-1.319 E.01145
G1 X188.749 Y180.285 E.13374
M73 P74 R4
G1 X188.749 Y179.75 E.01604
G1 X191.705 Y176.794 E.1251
G3 X191.533 Y176.43 I1.738 J-1.044 E.01206
G1 X188.749 Y179.214 E.11781
G1 X188.749 Y178.678 E.01604
G1 X191.398 Y176.03 E.11208
G3 X191.3 Y175.592 I2.144 J-.708 E.01346
G1 X188.749 Y178.142 E.10795
G1 X188.749 Y177.606 E.01604
G1 X191.253 Y175.102 E.10598
G3 X191.28 Y174.54 I4.196 J-.083 E.01686
G1 X188.749 Y177.071 E.10711
G1 X188.749 Y176.535 E.01604
G1 X191.733 Y173.551 E.12629
; WIPE_START
G1 X191.026 Y174.258 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.2 I1.107 J-.506 P1  F60000
G1 X189.346 Y170.58 Z3.2
G1 Z2.8
G1 E.4 F1800
G1 F14252.909
M204 S8000
G1 X188.749 Y171.177 E.02527
G1 X188.749 Y171.713 E.01604
G1 X189.713 Y170.749 E.04076
G1 X190.248 Y170.749 E.01604
G1 X188.749 Y172.248 E.06344
G1 X188.749 Y172.784 E.01604
G1 X190.784 Y170.749 E.08612
G1 X191.32 Y170.749 E.01604
G1 X188.749 Y173.32 E.10879
G1 X188.749 Y173.856 E.01604
G1 X191.856 Y170.749 E.13147
G1 X192.392 Y170.749 E.01604
G1 X188.749 Y174.392 E.15415
G1 X188.749 Y174.927 E.01604
G1 X192.927 Y170.749 E.17683
G1 X193.463 Y170.749 E.01604
G1 X188.749 Y175.463 E.19951
G1 X188.749 Y175.999 E.01604
G1 X193.999 Y170.749 E.22218
G1 X194.535 Y170.749 E.01604
G1 X193.854 Y171.43 E.0288
G3 X194.543 Y171.277 I1.464 J4.962 E.02114
G1 X195.071 Y170.749 E.02232
G1 X195.606 Y170.749 E.01604
G1 X195.101 Y171.254 E.02137
G3 X195.594 Y171.298 I.028 J2.48 E.01481
G1 X196.142 Y170.749 E.02322
G1 X196.678 Y170.749 E.01604
G1 X196.033 Y171.394 E.02729
G3 X196.429 Y171.534 I-.501 J2.05 E.01259
G1 X197.214 Y170.749 E.03321
G1 X197.75 Y170.749 E.01604
G1 X196.791 Y171.708 E.04055
G3 X197.123 Y171.912 I-.852 J1.758 E.01168
G1 X198.285 Y170.749 E.04919
G1 X198.821 Y170.749 E.01604
G1 X197.427 Y172.144 E.05903
G3 X197.703 Y172.404 I-1.161 J1.51 E.01136
G1 X199.357 Y170.749 E.07002
G1 X199.893 Y170.749 E.01604
G1 X197.951 Y172.691 E.08217
G3 X198.172 Y173.006 I-1.462 J1.262 E.01153
G1 X200.429 Y170.749 E.09549
G1 X200.964 Y170.749 E.01604
G1 X198.364 Y173.35 E.11006
G3 X198.524 Y173.726 I-1.799 J.985 E.01225
G1 X201.251 Y170.999 E.11541
G1 X201.251 Y171.535 E.01604
G1 X198.647 Y174.138 E.11019
G3 X198.728 Y174.593 I-2.236 J.632 E.01385
G1 X201.251 Y172.071 E.10677
G1 X201.251 Y172.607 E.01604
G1 X198.746 Y175.111 E.106
G3 X198.682 Y175.711 I-3.033 J-.02 E.01808
G1 X201.251 Y173.142 E.10871
G1 X201.251 Y173.678 E.01604
G1 X198.046 Y176.882 E.13562
; OBJECT_ID: 12
; COOLING_NODE: 0
; WIPE_START
G1 X198.753 Y176.175 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 16
M625
; start printing object, unique label id: 12
M624 AgAAAAAAAAA=
M204 S10000
G17
G3 Z3.2 I1.217 J-.027 P1  F60000
G1 X197.45 Y117.379 Z3.2
G1 Z2.8
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X197.274 Y117.549 E.00788
G3 X194.575 Y111.609 I-2.274 J-2.55 E.41147
G1 X194.915 Y111.583 E.01095
G3 X197.504 Y117.323 I.085 J3.416 E.25752
G1 X197.492 Y117.336 E.00056
; COOLING_NODE: 0
M204 S10000
G1 X197.166 Y117.087 F60000
G1 F13265.217
M204 S8000
G1 X197 Y117.247 E.00739
G3 X194.626 Y112.013 I-2.001 J-2.248 E.36233
G1 X194.925 Y111.991 E.00965
G3 X197.207 Y117.044 I.075 J3.008 E.22673
; COOLING_NODE: 0
M204 S10000
G1 X196.882 Y116.796 F60000
G1 F13265.217
M204 S8000
G1 X196.727 Y116.945 E.0069
G3 X194.676 Y112.417 I-1.727 J-1.946 E.31316
G1 X194.935 Y112.398 E.00834
G3 X196.923 Y116.752 I.065 J2.601 E.19537
; COOLING_NODE: 0
M204 S250
G1 X196.607 Y116.515 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X196.282 Y116.788 E.01264
G3 X194.725 Y112.807 I-1.282 J-1.793 E.23889
G1 X194.945 Y112.79 E.00656
G3 X196.641 Y116.467 I.055 J2.204 E.15281
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X196.282 Y116.788 E-.18289
G1 X195.909 Y117.015 E-.1659
G1 X195.831 Y117.041 E-.03121
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.2 I-1.132 J.448 P1  F60000
G1 X201.584 Y131.584 Z3.2
G1 Z2.8
M73 P74 R3
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y131.584 E.42342
G1 X188.416 Y110.416 E.68067
G1 X201.584 Y110.416 E.42342
G1 X201.584 Y131.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y131.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y131.991 E.4496
G1 X188.009 Y110.009 E.70685
G1 X201.991 Y110.009 E.4496
G1 X201.991 Y131.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y132.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y132.398 E.47578
G1 X187.602 Y109.602 E.73303
G1 X202.398 Y109.602 E.47578
G1 X202.398 Y132.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y132.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y132.79 E.46408
G1 X187.21 Y109.21 E.70237
G1 X202.79 Y109.21 E.46408
G1 X202.79 Y132.73 E.70058
; WIPE_START
M204 S8000
G1 X201.79 Y132.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.2 I.921 J-.796 P1  F60000
G1 X200.654 Y131.42 Z3.2
G1 Z2.8
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42179
G1 F14252.909
M204 S8000
G1 X201.251 Y130.824 E.02524
G1 X201.251 Y130.288 E.01604
G1 X200.288 Y131.251 E.04074
G1 X199.752 Y131.251 E.01604
G1 X201.251 Y129.752 E.06342
G1 X201.251 Y129.216 E.01604
G1 X199.216 Y131.251 E.08609
G1 X198.681 Y131.251 E.01604
G1 X201.251 Y128.681 E.10877
G1 X201.251 Y128.145 E.01604
G1 X198.145 Y131.251 E.13145
G1 X197.609 Y131.251 E.01604
G1 X201.251 Y127.609 E.15413
G1 X201.251 Y127.073 E.01604
G1 X197.073 Y131.251 E.1768
G1 X196.537 Y131.251 E.01604
G1 X201.251 Y126.537 E.19948
G1 X201.251 Y126.002 E.01604
G1 X196.002 Y131.251 E.22216
G1 X195.466 Y131.251 E.01604
G1 X201.251 Y125.466 E.24484
G1 X201.251 Y124.93 E.01604
G1 X194.93 Y131.251 E.26751
G1 X194.394 Y131.251 E.01604
G1 X201.251 Y124.394 E.29019
G1 X201.251 Y123.858 E.01604
G1 X193.858 Y131.251 E.31287
G1 X193.323 Y131.251 E.01604
G1 X201.251 Y123.323 E.33555
G1 X201.251 Y122.787 E.01604
G1 X192.787 Y131.251 E.35823
G1 X192.251 Y131.251 E.01604
G1 X201.251 Y122.251 E.3809
G1 X201.251 Y121.715 E.01604
G1 X191.715 Y131.251 E.40358
G1 X191.179 Y131.251 E.01604
G1 X201.251 Y121.179 E.42626
G1 X201.251 Y120.644 E.01604
G1 X190.644 Y131.251 E.44894
G1 X190.108 Y131.251 E.01604
G1 X201.251 Y120.108 E.47161
G1 X201.251 Y119.572 E.01604
G1 X189.572 Y131.251 E.49429
G1 X189.036 Y131.251 E.01604
G1 X201.251 Y119.036 E.51697
G1 X201.251 Y118.5 E.01604
G1 X188.749 Y131.001 E.5291
G1 X188.749 Y130.466 E.01604
G1 X201.251 Y117.965 E.5291
G1 X201.251 Y117.429 E.01604
G1 X188.749 Y129.93 E.5291
G1 X188.749 Y129.394 E.01604
G1 X201.251 Y116.893 E.5291
G1 X201.251 Y116.357 E.01604
G1 X188.749 Y128.858 E.5291
G1 X188.749 Y128.322 E.01604
G1 X201.251 Y115.821 E.5291
G1 X201.251 Y115.286 E.01604
G1 X188.749 Y127.787 E.5291
G1 X188.749 Y127.251 E.01604
G1 X201.251 Y114.75 E.5291
G1 X201.251 Y114.214 E.01604
G1 X188.749 Y126.715 E.5291
G1 X188.749 Y126.179 E.01604
G1 X196.487 Y118.442 E.32749
G3 X195.714 Y118.679 I-1.547 J-3.662 E.02424
G1 X188.749 Y125.643 E.29477
G1 X188.749 Y125.108 E.01604
G1 X195.108 Y118.749 E.26911
G3 X194.596 Y118.726 I-.003 J-5.446 E.01535
G1 X188.749 Y124.572 E.24744
G1 X188.749 Y124.036 E.01604
G1 X194.14 Y118.645 E.22816
G3 X193.725 Y118.524 I.396 J-2.134 E.01296
G1 X188.749 Y123.5 E.21059
G1 X188.749 Y122.964 E.01604
G1 X193.348 Y118.366 E.19465
G3 X193.004 Y118.174 I.784 J-1.818 E.01181
G1 X188.749 Y122.429 E.18007
G1 X188.749 Y121.893 E.01604
G1 X192.689 Y117.953 E.16674
G3 X192.402 Y117.705 I1.098 J-1.557 E.01139
G1 X188.749 Y121.357 E.15459
G1 X188.749 Y120.821 E.01604
G1 X192.142 Y117.429 E.14359
G3 X191.909 Y117.125 I1.402 J-1.316 E.01146
G1 X188.749 Y120.285 E.13374
G1 X188.749 Y119.75 E.01604
G1 X191.705 Y116.794 E.1251
G3 X191.533 Y116.43 I1.733 J-1.042 E.01206
G1 X188.749 Y119.214 E.11781
G1 X188.749 Y118.678 E.01604
G1 X191.398 Y116.03 E.11208
G3 X191.3 Y115.592 I2.145 J-.708 E.01346
G1 X188.749 Y118.142 E.10795
G1 X188.749 Y117.606 E.01604
G1 X191.253 Y115.102 E.10598
G3 X191.28 Y114.54 I4.198 J-.083 E.01686
G1 X188.749 Y117.071 E.10711
G1 X188.749 Y116.535 E.01604
G1 X191.722 Y113.562 E.1258
; WIPE_START
G1 X191.015 Y114.27 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.2 I1.109 J-.501 P1  F60000
G1 X189.346 Y110.58 Z3.2
G1 Z2.8
M73 P75 R3
G1 E.4 F1800
G1 F14252.909
M204 S8000
G1 X188.749 Y111.177 E.02527
G1 X188.749 Y111.713 E.01604
G1 X189.713 Y110.749 E.04076
G1 X190.248 Y110.749 E.01604
G1 X188.749 Y112.248 E.06344
G1 X188.749 Y112.784 E.01604
G1 X190.784 Y110.749 E.08612
G1 X191.32 Y110.749 E.01604
G1 X188.749 Y113.32 E.10879
G1 X188.749 Y113.856 E.01604
G1 X191.856 Y110.749 E.13147
G1 X192.392 Y110.749 E.01604
G1 X188.749 Y114.392 E.15415
G1 X188.749 Y114.927 E.01604
G1 X192.927 Y110.749 E.17683
G1 X193.463 Y110.749 E.01604
G1 X188.749 Y115.463 E.19951
G1 X188.749 Y115.999 E.01604
G1 X193.999 Y110.749 E.22218
G1 X194.535 Y110.749 E.01604
G1 X193.854 Y111.43 E.0288
G3 X194.543 Y111.277 I1.466 J4.97 E.02114
G1 X195.071 Y110.749 E.02232
G1 X195.606 Y110.749 E.01604
G1 X195.101 Y111.254 E.02137
G3 X195.594 Y111.298 I.027 J2.483 E.01481
G1 X196.142 Y110.749 E.02322
G1 X196.678 Y110.749 E.01604
G1 X196.033 Y111.394 E.02729
G3 X196.429 Y111.534 I-.5 J2.047 E.01259
G1 X197.214 Y110.749 E.03321
G1 X197.75 Y110.749 E.01604
G1 X196.791 Y111.708 E.04055
G3 X197.123 Y111.912 I-.853 J1.759 E.01168
G1 X198.285 Y110.749 E.04919
G1 X198.821 Y110.749 E.01604
G1 X197.427 Y112.144 E.05903
G3 X197.703 Y112.404 I-1.16 J1.509 E.01136
G1 X199.357 Y110.749 E.07002
G1 X199.893 Y110.749 E.01604
G1 X197.951 Y112.691 E.08217
G3 X198.172 Y113.006 I-1.463 J1.262 E.01153
G1 X200.429 Y110.749 E.09549
G1 X200.964 Y110.749 E.01604
G1 X198.364 Y113.35 E.11006
G3 X198.524 Y113.726 I-1.799 J.985 E.01225
G1 X201.251 Y110.999 E.11541
G1 X201.251 Y111.535 E.01604
G1 X198.647 Y114.138 E.11019
G3 X198.728 Y114.593 I-2.236 J.632 E.01385
G1 X201.251 Y112.071 E.10677
G1 X201.251 Y112.607 E.01604
G1 X198.746 Y115.111 E.106
G3 X198.682 Y115.711 I-3.033 J-.02 E.01808
G1 X201.251 Y113.142 E.1087
G1 X201.251 Y113.678 E.01604
G1 X198.046 Y116.883 E.13562
; OBJECT_ID: 8
; COOLING_NODE: 0
; WIPE_START
G1 X198.753 Y116.175 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 12
M625
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z3.2 I.015 J-1.217 P1  F60000
G1 X157.584 Y115.684 Z3.2
G1 Z2.8
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X112.416 Y115.684 E1.45243
G1 X112.416 Y113.516 E.0697
G1 X157.584 Y113.516 E1.45243
G1 X157.584 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X157.991 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X112.009 Y116.091 E1.47861
G1 X112.009 Y113.109 E.09588
G1 X157.991 Y113.109 E1.47861
G1 X157.991 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X158.398 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X111.602 Y116.498 E1.50479
G1 X111.602 Y112.702 E.12206
G1 X158.398 Y112.702 E1.50479
G1 X158.398 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X158.79 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F2504
M204 S5000
G1 X111.21 Y116.89 E1.41725
G1 X111.21 Y112.31 E.13642
G1 X158.79 Y112.31 E1.41725
G1 X158.79 Y116.83 E.13464
; WIPE_START
G1 F12000
M204 S8000
G1 X157.79 Y116.831 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.2 I1.175 J-.315 P1  F60000
G1 X157.192 Y114.6 Z3.2
G1 Z2.8
G1 E.4 F1800
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.41999
G1 F12000
M204 S8000
G1 X157.192 Y113.908 E.0206
G1 X136.584 Y113.908 E.61382
G1 X136.584 Y115.292 E.04121
G1 X157.192 Y115.292 E.61382
G1 X157.192 Y114.66 E.01882
M204 S10000
G1 X156.752 Y114.6 F60000
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X156.752 Y114.348 E.01
G1 X137.024 Y114.348 E.78415
G1 X137.024 Y114.852 E.02
G1 X156.752 Y114.852 E.78415
G1 X156.752 Y114.66 E.00762
; WIPE_START
G1 X156.752 Y114.852 E-.07281
G1 X155.943 Y114.852 E-.30719
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.2 I-.022 J-1.217 P1  F60000
G1 X129.468 Y115.336 Z3.2
G1 Z2.8
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X129.862 Y113.864 E.04897
G1 X124.269 Y115.336 E.18598
G1 X124.359 Y115.336 E.00292
G1 X124.754 Y113.864 E.04897
G1 X124.993 Y113.864 E.00769
G1 X121.271 Y114.862 E.12389
G1 X121.271 Y114.281 E.01866
G1 X122.325 Y115.336 E.04794
G1 X121.805 Y115.336 E.01673
G1 X122.199 Y113.864 E.04897
G1 X122.599 Y113.864 E.01284
G1 X124.07 Y115.336 E.0669
G1 X123.082 Y115.336 E.03176
G1 X123.476 Y113.864 E.04897
G1 X122.802 Y113.864 E.02168
; WIPE_START
G1 X123.476 Y113.864 E-.25616
G1 X123.392 Y114.179 E-.12384
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.2 I.382 J1.155 P1  F60000
G1 X124.343 Y113.864 Z3.2
G1 Z2.8
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X125.814 Y115.336 E.0669
G1 X125.636 Y115.336 E.00572
G1 X126.031 Y113.864 E.04897
G1 X127.559 Y115.336 E.06821
G1 X128.191 Y115.336 E.02031
G1 X128.585 Y113.864 E.04897
M204 S10000
G1 X129.362 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X129.577 Y113.864 E.0069
G1 X131.048 Y115.336 E.0669
G1 X130.745 Y115.336 E.00975
G1 X131.139 Y113.864 E.04897
G1 X131.321 Y113.864 E.00587
G1 X132.793 Y115.336 E.0669
G1 X132.022 Y115.336 E.02478
G1 X132.416 Y113.864 E.04897
G1 X133.066 Y113.864 E.0209
G1 X134.537 Y115.336 E.0669
M204 S10000
G1 X134.576 Y115.336 F60000
G1 F13265.217
M204 S8000
G1 X134.97 Y113.864 E.04897
G1 X134.811 Y113.864 E.00514
G1 X136.192 Y115.246 E.06283
G1 X136.192 Y115.336 E.00288
G1 X135.853 Y115.336 E.0109
G1 X136.192 Y114.071 E.04211
G1 X136.192 Y114.695 E.02007
G1 X133.801 Y115.336 E.0796
G1 X133.299 Y115.336 E.01614
G1 X133.693 Y113.864 E.04897
M204 S10000
G1 X134.128 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X134.525 Y113.864 E.01275
G1 X129.035 Y115.336 E.18277
G1 X129.303 Y115.336 E.00864
G1 X127.832 Y113.864 E.0669
G1 X127.308 Y113.864 E.01687
G1 X126.914 Y115.336 E.04897
G1 X126.018 Y115.336 E.0288
; WIPE_START
G1 X126.914 Y115.336 E-.34032
G1 X126.941 Y115.235 E-.03968
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.2 I-.011 J-1.217 P1  F60000
G1 X120.879 Y115.292 Z3.2
G1 Z2.8
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X120.879 Y113.908 E.04121
G1 X112.808 Y113.908 E.2404
G1 X112.808 Y115.292 E.04121
G1 X120.819 Y115.292 E.23861
M204 S10000
G1 X120.439 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X120.439 Y114.348 E.02
G1 X113.248 Y114.348 E.28582
G1 X113.248 Y114.852 E.02
G1 X120.379 Y114.852 E.28344
; COOLING_NODE: 0
; WIPE_START
G1 X119.379 Y114.852 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.2 I-1.054 J.608 P1  F60000
G1 X153.976 Y174.902 Z3.2
G1 Z2.8
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X156.024 Y174.902 E.06587
G1 X156.024 Y175.698 E.02559
G1 X153.976 Y175.698 E.06587
G1 X153.976 Y174.962 E.02366
; COOLING_NODE: 0
M204 S250
G1 X153.584 Y174.51 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F2504
M204 S5000
G1 X156.416 Y174.51 E.08437
G1 X156.416 Y176.09 E.04706
G1 X153.584 Y176.09 E.08437
G1 X153.584 Y174.57 E.04528
M204 S10000
M73 P76 R3
G1 X154.179 Y175.3 F60000
; FEATURE: Gap infill
; LINE_WIDTH: 0.43172
G1 F13888.888
M204 S8000
G1 X155.821 Y175.3 E.05041
; COOLING_NODE: 0
; WIPE_START
G1 X154.821 Y175.3 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.2 I.038 J-1.216 P1  F60000
G1 X142.024 Y174.902 Z3.2
G1 Z2.8
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X142.024 Y175.698 E.02559
G1 X139.976 Y175.698 E.06587
G1 X139.976 Y174.902 E.02559
G1 X141.964 Y174.902 E.06394
; COOLING_NODE: 0
M204 S250
G1 X142.416 Y174.51 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F2504
M204 S5000
G1 X142.416 Y176.09 E.04706
G1 X139.584 Y176.09 E.08437
G1 X139.584 Y174.51 E.04706
G1 X142.356 Y174.51 E.08259
M204 S10000
G1 X141.821 Y175.3 F60000
; FEATURE: Gap infill
; LINE_WIDTH: 0.43172
G1 F13888.888
M204 S8000
G1 X140.179 Y175.3 E.05041
; CHANGE_LAYER
; Z_HEIGHT: 3
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F13888.888
G1 X141.179 Y175.3 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 15/27
; update layer progress
M73 L15
M991 S0 P14 ;notify layer change
; OBJECT_ID: 16
; COOLING_NODE: 0
; start printing object, unique label id: 16
M624 BAAAAAAAAAA=
M204 S10000
G17
G3 Z3.2 I-.069 J1.215 P1  F60000
G1 X195.357 Y178.392 Z3.2
G1 Z3
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X195.256 Y178.406 E.00328
G3 X194.575 Y171.609 I-.255 J-3.407 E.33968
G1 X194.915 Y171.583 E.01096
G3 X195.76 Y178.33 I.085 J3.416 E.32327
G1 X195.416 Y178.383 E.01119
; COOLING_NODE: 0
M204 S10000
G1 X195.298 Y177.99 F60000
G1 F13265.217
M204 S8000
G1 X195.225 Y178 E.00235
G3 X194.626 Y172.013 I-.225 J-3.001 E.29919
G1 X194.925 Y171.991 E.00966
G3 X195.669 Y177.933 I.075 J3.009 E.28473
G1 X195.357 Y177.981 E.01017
; COOLING_NODE: 0
M204 S10000
G1 X195.238 Y177.588 F60000
G1 F13265.217
M204 S8000
G1 X195.195 Y177.594 E.00141
G3 X194.676 Y172.417 I-.194 J-2.595 E.25869
G1 X194.935 Y172.398 E.00835
G3 X195.579 Y177.536 I.065 J2.601 E.24619
G1 X195.297 Y177.579 E.00916
; COOLING_NODE: 0
M204 S250
G1 X195.18 Y177.202 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X195.165 Y177.203 E.00045
G3 X194.725 Y172.807 I-.165 J-2.204 E.2035
G1 X194.945 Y172.79 E.00657
G3 X195.492 Y177.154 I.055 J2.209 E.19366
G1 X195.24 Y177.193 E.0076
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X195.165 Y177.203 E-.02858
G1 X194.835 Y177.204 E-.12549
G1 X194.401 Y177.128 E-.16727
G1 X194.258 Y177.071 E-.05866
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.4 I-1.086 J.548 P1  F60000
G1 X201.584 Y191.584 Z3.4
G1 Z3
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y191.584 E.42342
G1 X188.416 Y170.416 E.68067
G1 X201.584 Y170.416 E.42342
G1 X201.584 Y191.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y191.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y191.991 E.4496
G1 X188.009 Y170.009 E.70685
G1 X201.991 Y170.009 E.4496
G1 X201.991 Y191.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y192.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y192.398 E.47578
G1 X187.602 Y169.602 E.73303
G1 X202.398 Y169.602 E.47578
G1 X202.398 Y192.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y192.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y192.79 E.46408
G1 X187.21 Y169.21 E.70237
G1 X202.79 Y169.21 E.46408
G1 X202.79 Y192.73 E.70058
; object ids of layer 15 start: 8,12,16
M624 BwAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer15 end: 8,12,16
M625
; WIPE_START
M204 S8000
G1 X201.79 Y192.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.4 I1.215 J-.077 P1  F60000
G1 X201.42 Y186.884 Z3.4
G1 Z3
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42179
G1 F14252.909
M204 S8000
G1 X188.749 Y174.213 E.53628
G1 X188.749 Y174.749 E.01604
G1 X201.251 Y187.25 E.5291
G1 X201.251 Y187.786 E.01604
G1 X188.749 Y175.285 E.5291
G1 X188.749 Y175.821 E.01604
G1 X201.251 Y188.322 E.5291
G1 X201.251 Y188.858 E.01604
G1 X188.749 Y176.357 E.5291
G1 X188.749 Y176.892 E.01604
G1 X201.251 Y189.393 E.5291
G1 X201.251 Y189.929 E.01604
G1 X188.749 Y177.428 E.5291
G1 X188.749 Y177.964 E.01604
G1 X201.251 Y190.465 E.5291
G1 X201.251 Y191.001 E.01604
G1 X188.749 Y178.5 E.5291
G1 X188.749 Y179.036 E.01604
G1 X200.964 Y191.251 E.51699
G1 X200.429 Y191.251 E.01604
G1 X188.749 Y179.571 E.49431
G1 X188.749 Y180.107 E.01604
G1 X199.893 Y191.251 E.47164
G1 X199.357 Y191.251 E.01604
G1 X188.749 Y180.643 E.44896
G1 X188.749 Y181.179 E.01604
G1 X198.821 Y191.251 E.42628
G1 X198.285 Y191.251 E.01604
G1 X188.749 Y181.715 E.4036
G1 X188.749 Y182.25 E.01604
G1 X197.75 Y191.251 E.38093
G1 X197.214 Y191.251 E.01604
G1 X188.749 Y182.786 E.35825
G1 X188.749 Y183.322 E.01604
G1 X196.678 Y191.251 E.33557
G1 X196.142 Y191.251 E.01604
G1 X188.749 Y183.858 E.31289
G1 X188.749 Y184.394 E.01604
G1 X195.606 Y191.251 E.29022
G1 X195.071 Y191.251 E.01604
G1 X188.749 Y184.929 E.26754
G1 X188.749 Y185.465 E.01604
G1 X194.535 Y191.251 E.24486
G1 X193.999 Y191.251 E.01604
G1 X188.749 Y186.001 E.22218
G1 X188.749 Y186.537 E.01604
G1 X193.463 Y191.251 E.19951
G1 X192.927 Y191.251 E.01604
G1 X188.749 Y187.073 E.17683
G1 X188.749 Y187.608 E.01604
G1 X192.392 Y191.251 E.15415
G1 X191.856 Y191.251 E.01604
G1 X188.749 Y188.144 E.13147
G1 X188.749 Y188.68 E.01604
G1 X191.32 Y191.251 E.10879
G1 X190.784 Y191.251 E.01604
G1 X188.749 Y189.216 E.08612
G1 X188.749 Y189.752 E.01604
G1 X190.248 Y191.251 E.06344
G1 X189.713 Y191.251 E.01604
G1 X188.749 Y190.287 E.04076
G1 X188.749 Y190.823 E.01604
G1 X189.346 Y191.42 E.02527
; WIPE_START
G1 X188.749 Y190.823 E-.3208
G1 X188.749 Y190.667 E-.0592
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.4 I1.157 J.377 P1  F60000
G1 X195.296 Y170.58 Z3.4
G1 Z3
G1 E.4 F1800
G1 F14252.909
M204 S8000
G1 X196.15 Y171.434 E.03613
G2 X195.462 Y171.282 I-1.157 J3.604 E.02111
G1 X194.93 Y170.749 E.02252
G1 X194.394 Y170.749 E.01604
G1 X194.895 Y171.25 E.0212
G2 X194.408 Y171.3 I.003 J2.459 E.01466
G1 X193.858 Y170.749 E.02328
G1 X193.323 Y170.749 E.01604
G1 X193.97 Y171.397 E.02742
G2 X193.572 Y171.535 I.49 J2.059 E.01263
G1 X192.787 Y170.749 E.03325
G1 X192.251 Y170.749 E.01604
G1 X193.209 Y171.707 E.04055
G2 X192.877 Y171.911 I.849 J1.761 E.01168
G1 X191.715 Y170.749 E.04916
G1 X191.179 Y170.749 E.01604
G1 X192.573 Y172.143 E.05898
G2 X192.302 Y172.408 I.897 J1.185 E.01137
G1 X190.644 Y170.749 E.07021
G1 X190.108 Y170.749 E.01604
G1 X192.049 Y172.69 E.08215
G2 X191.829 Y173.007 I1.468 J1.255 E.01154
G1 X189.572 Y170.749 E.09553
G1 X189.036 Y170.749 E.01604
G1 X191.636 Y173.349 E.11004
G2 X191.476 Y173.726 I1.801 J.986 E.01225
G1 X188.749 Y170.999 E.11542
G1 X188.749 Y171.534 E.01604
G1 X191.353 Y174.138 E.11019
G2 X191.272 Y174.593 I2.234 J.632 E.01385
G1 X188.749 Y172.07 E.10677
G1 X188.749 Y172.606 E.01604
G1 X191.254 Y175.11 E.106
G2 X191.318 Y175.71 I3.026 J-.019 E.01808
G1 X188.749 Y173.142 E.1087
G1 X188.749 Y173.678 E.01604
G1 X191.556 Y176.484 E.11878
G2 X193.511 Y178.439 I3.416 J-1.461 E.08478
G1 X201.251 Y186.179 E.32759
G1 X201.251 Y185.643 E.01604
G1 X194.289 Y178.681 E.29466
G2 X194.889 Y178.745 I.746 J-4.126 E.01808
G1 X201.251 Y185.107 E.26925
G1 X201.251 Y184.571 E.01604
G1 X195.405 Y178.725 E.24742
G2 X195.864 Y178.649 I-.605 J-5.076 E.01395
G1 X201.251 Y184.035 E.22797
G1 X201.251 Y183.5 E.01604
G1 X196.276 Y178.525 E.21057
G2 X196.651 Y178.364 I-.614 J-1.958 E.01224
G1 X201.251 Y182.964 E.19467
G1 X201.251 Y182.428 E.01604
G1 X196.995 Y178.172 E.18013
G2 X197.309 Y177.951 I-.948 J-1.682 E.01153
G1 X201.251 Y181.892 E.16681
G1 X201.251 Y181.356 E.01604
G1 X197.596 Y177.702 E.15467
G2 X197.856 Y177.426 I-1.247 J-1.433 E.01136
G1 X201.251 Y180.821 E.14368
G1 X201.251 Y180.285 E.01604
G1 X198.085 Y177.119 E.134
G1 X198.293 Y176.791 E.01161
G1 X201.251 Y179.749 E.12518
G1 X201.251 Y179.213 E.01604
G1 X198.467 Y176.43 E.11781
G2 X198.604 Y176.031 I-1.923 J-.884 E.01264
G1 X201.251 Y178.677 E.11201
G1 X201.251 Y178.142 E.01604
G1 X198.7 Y175.591 E.10794
G2 X198.747 Y175.102 I-2.423 J-.477 E.01474
G1 X201.251 Y177.606 E.10598
G1 X201.251 Y177.07 E.01604
G1 X198.72 Y174.539 E.10711
G2 X198.57 Y173.854 I-4.414 J.604 E.02101
G1 X201.251 Y176.534 E.11344
G1 X201.251 Y175.998 E.01604
G1 X196.002 Y170.749 E.22216
G1 X196.537 Y170.749 E.01604
G1 X201.251 Y175.463 E.19948
G1 X201.251 Y174.927 E.01604
G1 X197.073 Y170.749 E.1768
G1 X197.609 Y170.749 E.01604
G1 X201.251 Y174.391 E.15413
G1 X201.251 Y173.855 E.01604
G1 X198.145 Y170.749 E.13145
M73 P77 R3
G1 X198.681 Y170.749 E.01604
G1 X201.251 Y173.319 E.10877
G1 X201.251 Y172.784 E.01604
G1 X199.216 Y170.749 E.08609
G1 X199.752 Y170.749 E.01604
G1 X201.251 Y172.248 E.06342
G1 X201.251 Y171.712 E.01604
G1 X200.288 Y170.749 E.04074
G1 X200.824 Y170.749 E.01604
G1 X201.42 Y171.346 E.02524
; OBJECT_ID: 12
; COOLING_NODE: 0
; WIPE_START
G1 X200.824 Y170.749 E-.3205
G1 X200.667 Y170.749 E-.0595
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 16
M625
; start printing object, unique label id: 12
M624 AgAAAAAAAAA=
M204 S10000
G17
G3 Z3.4 I1.215 J-.071 P1  F60000
G1 X197.557 Y117.259 Z3.4
G1 Z3
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X197.504 Y117.323 E.00268
G3 X194.575 Y111.609 I-2.504 J-2.324 E.42182
G1 X194.915 Y111.583 E.01095
G3 X197.84 Y116.898 I.085 J3.415 E.24009
G1 X197.594 Y117.212 E.0128
; COOLING_NODE: 0
M204 S10000
G1 X197.166 Y117.087 F60000
G1 F13265.217
M204 S8000
G1 X196.99 Y117.256 E.00784
G3 X194.626 Y112.013 I-1.99 J-2.257 E.36186
G1 X194.925 Y111.991 E.00965
G3 X197.208 Y117.044 I.075 J3.008 E.2267
; COOLING_NODE: 0
M204 S10000
G1 X196.882 Y116.796 F60000
G1 F13265.217
M204 S8000
G1 X196.721 Y116.95 E.00718
G3 X194.676 Y112.417 I-1.721 J-1.951 E.31288
G1 X194.935 Y112.398 E.00834
G3 X196.923 Y116.752 I.065 J2.601 E.19534
; COOLING_NODE: 0
M204 S250
G1 X196.607 Y116.515 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X196.284 Y116.786 E.01257
G3 X194.725 Y112.807 I-1.285 J-1.792 E.23897
G1 X194.945 Y112.79 E.00656
G3 X196.641 Y116.467 I.055 J2.204 E.1528
; COOLING_NODE: 0
; WIPE_START
M204 S8000
G1 X196.284 Y116.786 E-.18204
G1 X195.909 Y117.015 E-.16695
G1 X195.832 Y117.041 E-.03101
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.4 I-1.132 J.448 P1  F60000
G1 X201.584 Y131.584 Z3.4
G1 Z3
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X188.416 Y131.584 E.42342
G1 X188.416 Y110.416 E.68067
G1 X201.584 Y110.416 E.42342
G1 X201.584 Y131.524 E.67874
; COOLING_NODE: 0
M204 S10000
G1 X201.991 Y131.991 F60000
G1 F13265.217
M204 S8000
G1 X188.009 Y131.991 E.4496
G1 X188.009 Y110.009 E.70685
G1 X201.991 Y110.009 E.4496
G1 X201.991 Y131.931 E.70492
; COOLING_NODE: 0
M204 S10000
G1 X202.398 Y132.398 F60000
G1 F13265.217
M204 S8000
G1 X187.602 Y132.398 E.47578
G1 X187.602 Y109.602 E.73303
G1 X202.398 Y109.602 E.47578
G1 X202.398 Y132.338 E.7311
; COOLING_NODE: 1
M204 S250
G1 X202.79 Y132.79 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X187.21 Y132.79 E.46408
G1 X187.21 Y109.21 E.70237
G1 X202.79 Y109.21 E.46408
G1 X202.79 Y132.73 E.70058
; WIPE_START
M204 S8000
G1 X201.79 Y132.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.4 I1.215 J-.077 P1  F60000
G1 X201.42 Y126.884 Z3.4
G1 Z3
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.42179
G1 F14252.909
M204 S8000
G1 X188.749 Y114.213 E.53628
G1 X188.749 Y114.749 E.01604
G1 X201.251 Y127.25 E.5291
G1 X201.251 Y127.786 E.01604
G1 X188.749 Y115.285 E.5291
G1 X188.749 Y115.821 E.01604
G1 X201.251 Y128.322 E.5291
G1 X201.251 Y128.858 E.01604
G1 X188.749 Y116.357 E.5291
G1 X188.749 Y116.892 E.01604
G1 X201.251 Y129.393 E.5291
G1 X201.251 Y129.929 E.01604
G1 X188.749 Y117.428 E.5291
G1 X188.749 Y117.964 E.01604
G1 X201.251 Y130.465 E.5291
G1 X201.251 Y131.001 E.01604
G1 X188.749 Y118.5 E.5291
G1 X188.749 Y119.036 E.01604
G1 X200.964 Y131.251 E.51699
G1 X200.429 Y131.251 E.01604
G1 X188.749 Y119.571 E.49431
G1 X188.749 Y120.107 E.01604
G1 X199.893 Y131.251 E.47164
G1 X199.357 Y131.251 E.01604
G1 X188.749 Y120.643 E.44896
G1 X188.749 Y121.179 E.01604
G1 X198.821 Y131.251 E.42628
G1 X198.285 Y131.251 E.01604
G1 X188.749 Y121.715 E.4036
G1 X188.749 Y122.25 E.01604
G1 X197.75 Y131.251 E.38093
G1 X197.214 Y131.251 E.01604
G1 X188.749 Y122.786 E.35825
G1 X188.749 Y123.322 E.01604
G1 X196.678 Y131.251 E.33557
G1 X196.142 Y131.251 E.01604
G1 X188.749 Y123.858 E.31289
G1 X188.749 Y124.394 E.01604
G1 X195.606 Y131.251 E.29022
G1 X195.071 Y131.251 E.01604
G1 X188.749 Y124.929 E.26754
G1 X188.749 Y125.465 E.01604
G1 X194.535 Y131.251 E.24486
G1 X193.999 Y131.251 E.01604
G1 X188.749 Y126.001 E.22218
G1 X188.749 Y126.537 E.01604
G1 X193.463 Y131.251 E.19951
G1 X192.927 Y131.251 E.01604
G1 X188.749 Y127.073 E.17683
G1 X188.749 Y127.608 E.01604
G1 X192.392 Y131.251 E.15415
G1 X191.856 Y131.251 E.01604
G1 X188.749 Y128.144 E.13147
G1 X188.749 Y128.68 E.01604
G1 X191.32 Y131.251 E.10879
G1 X190.784 Y131.251 E.01604
G1 X188.749 Y129.216 E.08612
G1 X188.749 Y129.752 E.01604
G1 X190.248 Y131.251 E.06344
G1 X189.713 Y131.251 E.01604
G1 X188.749 Y130.287 E.04076
G1 X188.749 Y130.823 E.01604
G1 X189.346 Y131.42 E.02527
; WIPE_START
G1 X188.749 Y130.823 E-.3208
G1 X188.749 Y130.667 E-.0592
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.4 I1.157 J.377 P1  F60000
G1 X195.296 Y110.58 Z3.4
G1 Z3
G1 E.4 F1800
G1 F14252.909
M204 S8000
G1 X196.15 Y111.433 E.03613
G2 X195.462 Y111.282 I-1.157 J3.606 E.02111
G1 X194.93 Y110.749 E.02252
G1 X194.394 Y110.749 E.01604
G1 X194.895 Y111.25 E.0212
G2 X194.408 Y111.3 I.002 J2.457 E.01466
G1 X193.858 Y110.749 E.02328
G1 X193.323 Y110.749 E.01604
G1 X193.97 Y111.397 E.02742
G2 X193.572 Y111.535 I.49 J2.058 E.01263
G1 X192.787 Y110.749 E.03325
G1 X192.251 Y110.749 E.01604
G1 X193.209 Y111.707 E.04055
G2 X192.877 Y111.911 I.849 J1.761 E.01168
G1 X191.715 Y110.749 E.04916
G1 X191.179 Y110.749 E.01604
G1 X192.573 Y112.143 E.05898
G2 X192.303 Y112.408 I.898 J1.185 E.01137
G1 X190.644 Y110.749 E.07021
G1 X190.108 Y110.749 E.01604
G1 X192.049 Y112.691 E.08215
G2 X191.829 Y113.007 I1.475 J1.26 E.01154
G1 X189.572 Y110.749 E.09553
G1 X189.036 Y110.749 E.01604
G1 X191.636 Y113.349 E.11004
G2 X191.476 Y113.725 I1.802 J.987 E.01225
G1 X188.749 Y110.999 E.11542
G1 X188.749 Y111.534 E.01604
G1 X191.353 Y114.138 E.11019
G2 X191.272 Y114.593 I2.234 J.632 E.01385
G1 X188.749 Y112.07 E.10677
G1 X188.749 Y112.606 E.01604
G1 X191.254 Y115.11 E.106
G2 X191.318 Y115.71 I3.026 J-.019 E.01808
G1 X188.749 Y113.142 E.1087
G1 X188.749 Y113.678 E.01604
G1 X191.556 Y116.484 E.11878
G2 X193.511 Y118.439 I3.425 J-1.471 E.08476
G1 X201.251 Y126.179 E.32759
G1 X201.251 Y125.643 E.01604
G1 X194.289 Y118.681 E.29466
G2 X194.889 Y118.745 I.746 J-4.121 E.01808
G1 X201.251 Y125.107 E.26925
G1 X201.251 Y124.571 E.01604
G1 X195.406 Y118.727 E.24735
G2 X195.864 Y118.649 I-.783 J-6 E.01391
G1 X201.251 Y124.035 E.22797
G1 X201.251 Y123.5 E.01604
G1 X196.276 Y118.525 E.21057
G2 X196.651 Y118.364 I-.613 J-1.956 E.01224
G1 X201.251 Y122.964 E.19467
G1 X201.251 Y122.428 E.01604
G1 X196.995 Y118.172 E.18013
G2 X197.309 Y117.951 I-.949 J-1.684 E.01153
G1 X201.251 Y121.892 E.16681
G1 X201.251 Y121.356 E.01604
G1 X197.596 Y117.702 E.15467
G2 X197.856 Y117.426 I-1.25 J-1.435 E.01136
G1 X201.251 Y120.821 E.14368
G1 X201.251 Y120.285 E.01604
G1 X198.084 Y117.119 E.13401
G1 X198.295 Y116.794 E.01159
G1 X201.251 Y119.749 E.12509
G1 X201.251 Y119.213 E.01604
G1 X198.467 Y116.43 E.11781
G2 X198.604 Y116.031 I-1.924 J-.884 E.01264
G1 X201.251 Y118.677 E.11201
G1 X201.251 Y118.142 E.01604
G1 X198.7 Y115.591 E.10794
G2 X198.747 Y115.102 I-2.425 J-.477 E.01474
G1 X201.251 Y117.606 E.10598
G1 X201.251 Y117.07 E.01604
G1 X198.72 Y114.539 E.10711
G2 X198.57 Y113.854 I-4.419 J.605 E.02101
G1 X201.251 Y116.534 E.11344
G1 X201.251 Y115.998 E.01604
G1 X196.002 Y110.749 E.22216
G1 X196.537 Y110.749 E.01604
G1 X201.251 Y115.463 E.19948
G1 X201.251 Y114.927 E.01604
G1 X197.073 Y110.749 E.1768
G1 X197.609 Y110.749 E.01604
G1 X201.251 Y114.391 E.15413
G1 X201.251 Y113.855 E.01604
G1 X198.145 Y110.749 E.13145
G1 X198.681 Y110.749 E.01604
G1 X201.251 Y113.319 E.10877
G1 X201.251 Y112.784 E.01604
G1 X199.216 Y110.749 E.08609
G1 X199.752 Y110.749 E.01604
G1 X201.251 Y112.248 E.06342
G1 X201.251 Y111.712 E.01604
G1 X200.288 Y110.749 E.04074
G1 X200.824 Y110.749 E.01604
G1 X201.42 Y111.346 E.02524
; OBJECT_ID: 8
; COOLING_NODE: 0
; WIPE_START
G1 X200.824 Y110.749 E-.3205
G1 X200.667 Y110.749 E-.0595
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 12
M625
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z3.4 I-.138 J-1.209 P1  F60000
G1 X157.584 Y115.684 Z3.4
G1 Z3
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
M73 P78 R3
G1 F13265.217
M204 S8000
G1 X112.416 Y115.684 E1.45243
G1 X112.416 Y113.516 E.0697
G1 X157.584 Y113.516 E1.45243
G1 X157.584 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X157.991 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X112.009 Y116.091 E1.47861
G1 X112.009 Y113.109 E.09588
G1 X157.991 Y113.109 E1.47861
G1 X157.991 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X158.398 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X111.602 Y116.498 E1.50479
G1 X111.602 Y112.702 E.12206
G1 X158.398 Y112.702 E1.50479
G1 X158.398 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X158.79 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F2346
M204 S5000
G1 X111.21 Y116.89 E1.41725
G1 X111.21 Y112.31 E.13642
G1 X158.79 Y112.31 E1.41725
G1 X158.79 Y116.83 E.13464
; WIPE_START
G1 F12000
M204 S8000
G1 X157.79 Y116.831 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.4 I1.175 J-.315 P1  F60000
G1 X157.192 Y114.6 Z3.4
G1 Z3
G1 E.4 F1800
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.41999
G1 F12000
M204 S8000
G1 X157.192 Y113.908 E.0206
G1 X136.584 Y113.908 E.61382
G1 X136.584 Y115.292 E.04121
G1 X157.192 Y115.292 E.61382
G1 X157.192 Y114.66 E.01882
M204 S10000
G1 X156.752 Y114.6 F60000
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X156.752 Y114.348 E.01
G1 X137.024 Y114.348 E.78415
G1 X137.024 Y114.852 E.02
G1 X156.752 Y114.852 E.78415
G1 X156.752 Y114.66 E.00762
; WIPE_START
G1 X156.752 Y114.852 E-.07281
G1 X155.943 Y114.852 E-.30719
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.4 I.052 J-1.216 P1  F60000
G1 X133.062 Y113.864 Z3.4
G1 Z3
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X132.27 Y113.864 E.0255
G1 X131.875 Y115.336 E.04897
G1 X131.248 Y115.336 E.02018
G1 X129.777 Y113.864 E.0669
M204 S10000
G1 X129.715 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X129.321 Y115.336 E.04897
G1 X128.248 Y115.336 E.03452
M204 S10000
G1 X127.555 Y115.336 F60000
G1 F13265.217
M204 S8000
G1 X126.767 Y115.336 E.02535
G1 X127.161 Y113.864 E.04897
G1 X126.288 Y113.864 E.02809
G1 X127.759 Y115.336 E.0669
G1 X128.044 Y115.336 E.00917
G1 X128.438 Y113.864 E.04897
G1 X128.032 Y113.864 E.01305
G1 X129.504 Y115.336 E.0669
G1 X135.071 Y113.864 E.18519
G1 X135.011 Y113.864 E.00196
G1 X136.192 Y115.046 E.05373
G1 X136.192 Y114.841 E.00658
G1 X134.347 Y115.336 E.06141
G1 X134.43 Y115.336 E.00265
G1 X134.824 Y113.864 E.04897
M204 S10000
G1 X135.275 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X136.101 Y113.864 E.02656
G1 X135.707 Y115.336 E.04897
G1 X136.192 Y115.336 E.01561
G1 X136.192 Y115.25 E.00277
; WIPE_START
G1 X136.192 Y115.336 E-.03269
G1 X135.707 Y115.336 E-.18443
G1 X135.818 Y114.922 E-.16288
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.4 I-.402 J-1.149 P1  F60000
G1 X134.633 Y115.336 Z3.4
G1 Z3
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X134.737 Y115.336 E.00334
G1 X133.266 Y113.864 E.0669
G1 X133.547 Y113.864 E.00903
G1 X133.153 Y115.336 E.04897
G1 X132.993 Y115.336 E.00514
G1 X131.521 Y113.864 E.0669
G1 X130.993 Y113.864 E.01701
G1 X130.598 Y115.336 E.04897
; WIPE_START
G1 X130.857 Y114.37 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.4 I1.206 J-.163 P1  F60000
G1 X130.789 Y113.864 Z3.4
G1 Z3
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X130.305 Y113.864 E.01556
G1 X124.815 Y115.336 E.18277
G1 X124.473 Y115.336 E.01099
; WIPE_START
G1 X124.815 Y115.336 E-.12982
G1 X125.451 Y115.165 E-.25018
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.4 I-1.186 J.272 P1  F60000
G1 X125.49 Y115.336 Z3.4
G1 Z3
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X125.884 Y113.864 E.04897
G1 X125.539 Y113.864 E.0111
G1 X121.043 Y115.069 E.14969
G1 X121.043 Y115.336 E.00856
G1 X121.659 Y115.336 E.01981
G1 X122.053 Y113.864 E.04897
G1 X121.054 Y113.864 E.03211
G1 X122.525 Y115.336 E.0669
G1 X122.936 Y115.336 E.0132
G1 X123.33 Y113.864 E.04897
G1 X122.799 Y113.864 E.01708
G1 X124.27 Y115.336 E.0669
G1 X124.213 Y115.336 E.00183
G1 X124.607 Y113.864 E.04897
M204 S10000
G1 X124.543 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X126.014 Y115.336 E.0669
; WIPE_START
G1 X125.307 Y114.628 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.4 I-.172 J-1.205 P1  F60000
G1 X120.651 Y115.292 Z3.4
G1 Z3
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X120.651 Y113.908 E.04121
G1 X112.808 Y113.908 E.2336
G1 X112.808 Y115.292 E.04121
G1 X120.591 Y115.292 E.23181
M204 S10000
G1 X120.211 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X120.211 Y114.348 E.02
G1 X113.248 Y114.348 E.27674
G1 X113.248 Y114.852 E.02
G1 X120.151 Y114.852 E.27436
; COOLING_NODE: 0
; WIPE_START
G1 X119.151 Y114.852 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.4 I-1.05 J.615 P1  F60000
G1 X154.319 Y174.902 Z3.4
G1 Z3
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X155.681 Y174.902 E.04377
G1 X155.681 Y175.698 E.02559
G1 X154.319 Y175.698 E.04377
G1 X154.319 Y174.962 E.02366
; COOLING_NODE: 0
M204 S250
G1 X153.927 Y174.51 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F2346
M204 S5000
G1 X156.073 Y174.51 E.06391
G1 X156.073 Y176.09 E.04706
G1 X153.927 Y176.09 E.06391
G1 X153.927 Y174.57 E.04528
M204 S10000
G1 X154.523 Y175.3 F60000
; FEATURE: Gap infill
; LINE_WIDTH: 0.43172
G1 F13888.888
M204 S8000
G1 X155.477 Y175.3 E.02931
; COOLING_NODE: 0
; WIPE_START
G1 X154.523 Y175.3 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.4 I.038 J-1.216 P1  F60000
G1 X141.681 Y174.902 Z3.4
G1 Z3
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X141.681 Y175.698 E.02559
G1 X140.319 Y175.698 E.04377
G1 X140.319 Y174.902 E.02559
G1 X141.621 Y174.902 E.04184
; COOLING_NODE: 0
M204 S250
G1 X142.073 Y174.51 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F2346
M204 S5000
G1 X142.073 Y176.09 E.04706
G1 X139.927 Y176.09 E.06391
G1 X139.927 Y174.51 E.04706
G1 X142.013 Y174.51 E.06212
M204 S10000
G1 X141.477 Y175.3 F60000
; FEATURE: Gap infill
; LINE_WIDTH: 0.43172
G1 F13888.888
M204 S8000
G1 X140.523 Y175.3 E.02931
; CHANGE_LAYER
; Z_HEIGHT: 3.2
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F13888.888
G1 X141.477 Y175.3 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 16/27
; update layer progress
M73 L16
M991 S0 P15 ;notify layer change
M106 S68.85
; OBJECT_ID: 16
; COOLING_NODE: 0
; start printing object, unique label id: 16
M624 BAAAAAAAAAA=
M204 S10000
G17
G3 Z3.4 I-.043 J1.216 P1  F60000
G1 X195.191 Y177.2 Z3.4
G1 Z3.2
G1 E.4 F1800
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X195.165 Y177.198 E.00079
G3 X194.725 Y172.807 I-.165 J-2.201 E.20325
G1 X194.945 Y172.79 E.00656
G3 X195.49 Y177.149 I.055 J2.206 E.19343
G1 X195.25 Y177.19 E.00726
; COOLING_NODE: 1
; WIPE_START
M204 S8000
G1 X195.165 Y177.198 E-.03268
G1 X194.835 Y177.204 E-.12529
G1 X194.399 Y177.127 E-.16836
G1 X194.267 Y177.075 E-.05368
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.6 I-1.07 J.58 P1  F60000
G1 X202.79 Y192.79 Z3.6
G1 Z3.2
G1 E.4 F1800
M73 P79 R3
G1 F12000
M204 S5000
G1 X187.21 Y192.79 E.46408
G1 X187.21 Y169.21 E.70237
G1 X202.79 Y169.21 E.46408
G1 X202.79 Y192.73 E.70058
; object ids of layer 16 start: 8,12,16
M624 BwAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer16 end: 8,12,16
M625
; WIPE_START
M204 S8000
G1 X201.79 Y192.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.6 I.948 J.763 P1  F60000
G1 X202.583 Y191.749 Z3.6
G1 Z3.2
G1 E.4 F1800
; FEATURE: Top surface
G1 F12000
M204 S2000
G1 X201.749 Y192.583 E.0351
G1 X201.616 Y192.716
G1 X201.082 Y192.716
G1 X201.216 Y192.583
G1 X202.583 Y191.216 E.05757
G1 X202.716 Y191.082
G1 X202.716 Y190.549
G1 X202.583 Y190.683
G1 X200.683 Y192.583 E.08003
G1 X200.549 Y192.716
G1 X200.016 Y192.716
G1 X200.15 Y192.583
G1 X202.583 Y190.15 E.10249
G1 X202.716 Y190.016
G1 X202.716 Y189.483
G1 X202.583 Y189.616
G1 X199.616 Y192.583 E.12496
G1 X199.483 Y192.716
G1 X198.949 Y192.716
G1 X199.083 Y192.583
G1 X202.583 Y189.083 E.14742
G1 X202.716 Y188.949
G1 X202.716 Y188.416
G1 X202.583 Y188.55
G1 X198.55 Y192.583 E.16988
G1 X198.416 Y192.716
G1 X197.883 Y192.716
G1 X198.017 Y192.583
G1 X202.583 Y188.017 E.19235
G1 X202.716 Y187.883
G1 X202.716 Y187.35
G1 X202.583 Y187.483
G1 X197.483 Y192.583 E.21481
G1 X197.35 Y192.716
G1 X196.816 Y192.716
G1 X196.95 Y192.583
G1 X202.583 Y186.95 E.23727
G1 X202.716 Y186.816
G1 X202.716 Y186.283
G1 X202.583 Y186.417
G1 X196.417 Y192.583 E.25974
G1 X196.283 Y192.716
G1 X195.75 Y192.716
G1 X195.883 Y192.583
G1 X202.583 Y185.883 E.2822
G1 X202.716 Y185.75
G1 X202.716 Y185.217
G1 X202.583 Y185.35
G1 X195.35 Y192.583 E.30466
G1 X195.217 Y192.716
G1 X194.683 Y192.716
G1 X194.817 Y192.583
G1 X202.583 Y184.817 E.32713
G1 X202.716 Y184.683
G1 X202.716 Y184.15
G1 X202.583 Y184.284
G1 X194.284 Y192.583 E.34959
G1 X194.15 Y192.716
G1 X193.617 Y192.716
G1 X193.75 Y192.583
G1 X202.583 Y183.75 E.37205
G1 X202.716 Y183.617
G1 X202.716 Y183.084
G1 X202.583 Y183.217
G1 X193.217 Y192.583 E.39452
G1 X193.084 Y192.716
G1 X192.55 Y192.716
G1 X192.684 Y192.583
G1 X202.583 Y182.684 E.41698
G1 X202.716 Y182.55
G1 X202.716 Y182.017
G1 X202.583 Y182.151
G1 X192.151 Y192.583 E.43944
G1 X192.017 Y192.716
G1 X191.484 Y192.716
G1 X191.617 Y192.583
G1 X202.583 Y181.617 E.4619
G1 X202.716 Y181.484
G1 X202.716 Y180.951
G1 X202.583 Y181.084
G1 X191.084 Y192.583 E.48437
G1 X190.951 Y192.716
G1 X190.417 Y192.716
G1 X190.551 Y192.583
G1 X202.583 Y180.551 E.50683
G1 X202.716 Y180.417
G1 X202.716 Y179.884
G1 X202.583 Y180.018
G1 X190.018 Y192.583 E.52929
G1 X189.884 Y192.716
G1 X189.351 Y192.716
G1 X189.484 Y192.583
G1 X202.583 Y179.484 E.55176
G1 X202.716 Y179.351
G1 X202.716 Y178.818
G1 X202.583 Y178.951
G1 X188.951 Y192.583 E.57422
G1 X188.817 Y192.716
G1 X188.284 Y192.716
G1 X188.418 Y192.583
G1 X202.583 Y178.418 E.59668
G1 X202.716 Y178.284
G1 X202.716 Y177.751
G1 X202.583 Y177.885
G1 X187.885 Y192.583 E.61915
G1 X187.751 Y192.716
G1 X187.284 Y192.65
G1 X187.417 Y192.517
G1 X202.583 Y177.351 E.63883
G1 X202.716 Y177.218
G1 X202.716 Y176.684
G1 X202.583 Y176.818
G1 X187.417 Y191.983 E.63883
G1 X187.284 Y192.117
G1 X187.284 Y191.584
G1 X187.417 Y191.45
G1 X202.583 Y176.285 E.63883
G1 X202.716 Y176.151
G1 X202.716 Y175.618
G1 X202.583 Y175.752
G1 X187.417 Y190.917 E.63883
G1 X187.284 Y191.05
G1 X187.284 Y190.517
G1 X187.417 Y190.384
G1 X202.583 Y175.218 E.63883
G1 X202.716 Y175.085
G1 X202.716 Y174.551
G1 X202.583 Y174.685
G1 X187.417 Y189.85 E.63883
G1 X187.284 Y189.984
G1 X187.284 Y189.451
G1 X187.417 Y189.317
G1 X202.583 Y174.152 E.63883
G1 X202.716 Y174.018
G1 X202.716 Y173.485
G1 X202.583 Y173.619
G1 X187.417 Y188.784 E.63883
G1 X187.284 Y188.917
G1 X187.284 Y188.384
G1 X187.417 Y188.251
G1 X202.583 Y173.085 E.63883
G1 X202.716 Y172.952
G1 X202.716 Y172.418
G1 X202.583 Y172.552
G1 X187.417 Y187.717 E.63883
G1 X187.284 Y187.851
G1 X187.284 Y187.318
G1 X187.417 Y187.184
G1 X202.583 Y172.019 E.63883
G1 X202.716 Y171.885
G1 X202.716 Y171.352
G1 X202.583 Y171.486
G1 X187.417 Y186.651 E.63883
G1 X187.284 Y186.784
G1 X187.284 Y186.251
G1 X187.417 Y186.118
G1 X202.583 Y170.952 E.63883
G1 X202.716 Y170.819
G1 X202.716 Y170.285
G1 X202.583 Y170.419
G1 X197.317 Y175.685 E.22181
G1 X197.183 Y175.818
G1 X197.273 Y175.195
G1 X197.407 Y175.062
G1 X202.583 Y169.886 E.21804
G1 X202.716 Y169.752
G1 X202.651 Y169.284
G1 X202.518 Y169.417
G1 X197.368 Y174.567 E.21694
G1 X197.234 Y174.701
G1 X197.119 Y174.283
G1 X197.253 Y174.149
G1 X201.985 Y169.417 E.19931
G1 X202.118 Y169.284
G1 X201.585 Y169.284
G1 X201.451 Y169.417
G1 X197.084 Y173.785 E.18397
G1 X196.95 Y173.918
G1 X196.734 Y173.601
G1 X196.868 Y173.468
G1 X200.918 Y169.417 E.17062
G1 X201.052 Y169.284
G1 X200.518 Y169.284
G1 X200.385 Y169.417
G1 X196.602 Y173.2 E.15936
G1 X196.468 Y173.334
G1 X196.163 Y173.106
G1 X196.296 Y172.972
G1 X199.851 Y169.417 E.14975
G1 X199.985 Y169.284
G1 X199.452 Y169.284
G1 X199.318 Y169.417
G1 X195.949 Y172.787 E.14194
G1 X195.815 Y172.921
G1 X195.416 Y172.787
G1 X195.549 Y172.653
G1 X198.785 Y169.417 E.1363
G1 X198.919 Y169.284
G1 X198.385 Y169.284
G1 X198.252 Y169.417
G1 X195.078 Y172.591 E.13367
G1 X194.945 Y172.724
G1 X194.354 Y172.782
G1 X194.487 Y172.648
G1 X197.718 Y169.417 E.13611
G1 X197.852 Y169.284
G1 X197.319 Y169.284
G1 X197.185 Y169.417
G1 X193.458 Y173.144 E.157
; WIPE_START
M204 S8000
G1 X194.165 Y172.437 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.6 I-1.161 J.364 P1  F60000
G1 X195.691 Y177.311 Z3.6
G1 Z3.2
G1 E.4 F1800
G1 F12000
M204 S2000
G1 X187.417 Y185.584 E.34851
G1 X187.284 Y185.718
G1 X187.284 Y185.185
G1 X187.417 Y185.051
G1 X195.063 Y177.406 E.32206
G1 X195.196 Y177.272
G1 X194.701 Y177.234
G1 X194.568 Y177.367
G1 X187.417 Y184.518 E.30121
G1 X187.284 Y184.651
G1 X187.284 Y184.118
G1 X187.417 Y183.985
G1 X194.15 Y177.252 E.28361
G1 X194.284 Y177.118
G1 X193.921 Y176.948
G1 X193.787 Y177.082
G1 X187.417 Y183.451 E.26832
G1 X187.284 Y183.585
G1 X187.284 Y183.052
G1 X187.417 Y182.918
G1 X193.468 Y176.867 E.25487
G1 X193.602 Y176.734
G1 X193.332 Y176.47
G1 X193.198 Y176.604
G1 X187.417 Y182.385 E.24351
G1 X187.284 Y182.518
G1 X187.284 Y181.985
G1 X187.417 Y181.851
G1 X192.972 Y176.297 E.23397
G1 X193.105 Y176.164
G1 X192.921 Y175.814
G1 X192.788 Y175.948
G1 X187.417 Y181.318 E.22622
G1 X187.284 Y181.452
G1 X187.284 Y180.919
M73 P80 R3
G1 X187.417 Y180.785
G1 X192.655 Y175.547 E.22065
G1 X192.789 Y175.413
G1 X192.727 Y174.942
G1 X192.593 Y175.076
G1 X187.417 Y180.252 E.21804
G1 X187.284 Y180.385
G1 X187.284 Y179.852
G1 X187.417 Y179.718
G1 X192.648 Y174.488 E.22035
G1 X192.782 Y174.354
G1 X193.32 Y173.282
G1 X193.187 Y173.416
G1 X187.417 Y179.185 E.24303
G1 X187.284 Y179.319
G1 X187.284 Y178.786
G1 X187.417 Y178.652
G1 X196.652 Y169.417 E.389
G1 X196.786 Y169.284
G1 X196.252 Y169.284
G1 X196.119 Y169.417
G1 X187.417 Y178.119 E.36654
G1 X187.284 Y178.252
G1 X187.284 Y177.719
G1 X187.417 Y177.585
G1 X195.585 Y169.417 E.34408
G1 X195.719 Y169.284
G1 X195.186 Y169.284
G1 X195.052 Y169.417
G1 X187.417 Y177.052 E.32161
G1 X187.284 Y177.186
G1 X187.284 Y176.653
G1 X187.417 Y176.519
G1 X194.519 Y169.417 E.29915
G1 X194.653 Y169.284
G1 X194.119 Y169.284
G1 X193.986 Y169.417
G1 X187.417 Y175.986 E.27669
G1 X187.284 Y176.119
G1 X187.284 Y175.586
G1 X187.417 Y175.452
G1 X193.452 Y169.417 E.25422
G1 X193.586 Y169.284
G1 X193.053 Y169.284
G1 X192.919 Y169.417
G1 X187.417 Y174.919 E.23176
G1 X187.284 Y175.053
G1 X187.284 Y174.52
G1 X187.417 Y174.386
G1 X192.386 Y169.417 E.2093
G1 X192.52 Y169.284
G1 X191.986 Y169.284
G1 X191.853 Y169.417
G1 X187.417 Y173.853 E.18683
G1 X187.284 Y173.986
G1 X187.284 Y173.453
G1 X187.417 Y173.319
G1 X191.319 Y169.417 E.16437
G1 X191.453 Y169.284
G1 X190.92 Y169.284
G1 X190.786 Y169.417
G1 X187.417 Y172.786 E.14191
G1 X187.284 Y172.92
G1 X187.284 Y172.386
G1 X187.417 Y172.253
G1 X190.253 Y169.417 E.11944
G1 X190.386 Y169.284
G1 X189.853 Y169.284
G1 X189.72 Y169.417
G1 X187.417 Y171.72 E.09698
G1 X187.284 Y171.853
G1 X187.284 Y171.32
G1 X187.417 Y171.186
G1 X189.186 Y169.417 E.07452
G1 X189.32 Y169.284
G1 X188.787 Y169.284
G1 X188.653 Y169.417
G1 X187.417 Y170.653 E.05205
G1 X187.284 Y170.787
G1 X187.284 Y170.253
G1 X187.417 Y170.12
G1 X188.12 Y169.417 E.02959
; WIPE_START
M204 S8000
G1 X187.417 Y170.12 E-.37749
G1 X187.413 Y170.124 E-.00251
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.6 I-.765 J.946 P1  F60000
G1 X196.097 Y177.145 Z3.6
G1 Z3.2
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.106693
G1 F15000
M204 S8000
G1 X196.006 Y177.208 E.00056
; LINE_WIDTH: 0.14373
G1 X195.915 Y177.271 E.00088
; LINE_WIDTH: 0.180172
G1 X195.824 Y177.334 E.0012
G1 X195.788 Y177.327 E.0004
; LINE_WIDTH: 0.150845
G1 X195.682 Y177.302 E.00092
; OBJECT_ID: 12
; COOLING_NODE: 0
; WIPE_START
G1 X195.788 Y177.327 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 16
M625
; start printing object, unique label id: 12
M624 AgAAAAAAAAA=
M204 S10000
G17
G3 Z3.6 I1.217 J.016 P1  F60000
G1 X196.607 Y116.515 Z3.6
G1 Z3.2
G1 E.4 F1800
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X196.284 Y116.786 E.01258
G3 X194.725 Y112.807 I-1.285 J-1.792 E.23896
G1 X194.945 Y112.79 E.00656
G3 X196.641 Y116.466 I.055 J2.204 E.15279
; COOLING_NODE: 1
; WIPE_START
M204 S8000
G1 X196.284 Y116.786 E-.18217
G1 X195.909 Y117.015 E-.16689
G1 X195.832 Y117.041 E-.03094
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.6 I-1.113 J.492 P1  F60000
G1 X202.79 Y132.79 Z3.6
G1 Z3.2
G1 E.4 F1800
G1 F12000
M204 S5000
G1 X187.21 Y132.79 E.46408
G1 X187.21 Y109.21 E.70237
G1 X202.79 Y109.21 E.46408
G1 X202.79 Y132.73 E.70058
; WIPE_START
M204 S8000
G1 X201.79 Y132.734 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.6 I.948 J.763 P1  F60000
G1 X202.583 Y131.749 Z3.6
G1 Z3.2
G1 E.4 F1800
; FEATURE: Top surface
G1 F12000
M204 S2000
G1 X201.749 Y132.583 E.0351
G1 X201.616 Y132.716
G1 X201.082 Y132.716
G1 X201.216 Y132.583
G1 X202.583 Y131.216 E.05757
G1 X202.716 Y131.082
G1 X202.716 Y130.549
G1 X202.583 Y130.683
G1 X200.683 Y132.583 E.08003
G1 X200.549 Y132.716
G1 X200.016 Y132.716
G1 X200.15 Y132.583
G1 X202.583 Y130.15 E.10249
G1 X202.716 Y130.016
G1 X202.716 Y129.483
G1 X202.583 Y129.616
G1 X199.616 Y132.583 E.12496
G1 X199.483 Y132.716
G1 X198.949 Y132.716
G1 X199.083 Y132.583
G1 X202.583 Y129.083 E.14742
G1 X202.716 Y128.949
G1 X202.716 Y128.416
G1 X202.583 Y128.55
G1 X198.55 Y132.583 E.16988
G1 X198.416 Y132.716
G1 X197.883 Y132.716
G1 X198.017 Y132.583
G1 X202.583 Y128.017 E.19235
G1 X202.716 Y127.883
G1 X202.716 Y127.35
G1 X202.583 Y127.483
G1 X197.483 Y132.583 E.21481
G1 X197.35 Y132.716
G1 X196.816 Y132.716
G1 X196.95 Y132.583
G1 X202.583 Y126.95 E.23727
G1 X202.716 Y126.816
G1 X202.716 Y126.283
G1 X202.583 Y126.417
G1 X196.417 Y132.583 E.25974
G1 X196.283 Y132.716
G1 X195.75 Y132.716
G1 X195.883 Y132.583
G1 X202.583 Y125.883 E.2822
G1 X202.716 Y125.75
G1 X202.716 Y125.217
G1 X202.583 Y125.35
G1 X195.35 Y132.583 E.30466
G1 X195.217 Y132.716
G1 X194.683 Y132.716
G1 X194.817 Y132.583
G1 X202.583 Y124.817 E.32713
G1 X202.716 Y124.683
G1 X202.716 Y124.15
G1 X202.583 Y124.284
G1 X194.284 Y132.583 E.34959
G1 X194.15 Y132.716
G1 X193.617 Y132.716
G1 X193.75 Y132.583
G1 X202.583 Y123.75 E.37205
G1 X202.716 Y123.617
G1 X202.716 Y123.084
G1 X202.583 Y123.217
G1 X193.217 Y132.583 E.39452
G1 X193.084 Y132.716
G1 X192.55 Y132.716
G1 X192.684 Y132.583
G1 X202.583 Y122.684 E.41698
G1 X202.716 Y122.55
G1 X202.716 Y122.017
G1 X202.583 Y122.151
G1 X192.151 Y132.583 E.43944
G1 X192.017 Y132.716
G1 X191.484 Y132.716
G1 X191.617 Y132.583
G1 X202.583 Y121.617 E.4619
G1 X202.716 Y121.484
G1 X202.716 Y120.951
G1 X202.583 Y121.084
G1 X191.084 Y132.583 E.48437
G1 X190.951 Y132.716
G1 X190.417 Y132.716
G1 X190.551 Y132.583
G1 X202.583 Y120.551 E.50683
G1 X202.716 Y120.417
G1 X202.716 Y119.884
G1 X202.583 Y120.018
G1 X190.018 Y132.583 E.52929
G1 X189.884 Y132.716
G1 X189.351 Y132.716
G1 X189.484 Y132.583
G1 X202.583 Y119.484 E.55176
G1 X202.716 Y119.351
G1 X202.716 Y118.817
G1 X202.583 Y118.951
G1 X188.951 Y132.583 E.57422
G1 X188.817 Y132.716
G1 X188.284 Y132.716
M73 P80 R2
G1 X188.418 Y132.583
G1 X202.583 Y118.418 E.59668
G1 X202.716 Y118.284
G1 X202.716 Y117.751
G1 X202.583 Y117.885
G1 X187.885 Y132.583 E.61915
G1 X187.751 Y132.716
G1 X187.284 Y132.65
G1 X187.417 Y132.517
G1 X202.583 Y117.351 E.63883
G1 X202.716 Y117.218
G1 X202.716 Y116.684
G1 X202.583 Y116.818
G1 X187.417 Y131.983 E.63883
G1 X187.284 Y132.117
G1 X187.284 Y131.584
G1 X187.417 Y131.45
G1 X202.583 Y116.285 E.63883
G1 X202.716 Y116.151
G1 X202.716 Y115.618
G1 X202.583 Y115.752
G1 X187.417 Y130.917 E.63883
G1 X187.284 Y131.05
G1 X187.284 Y130.517
G1 X187.417 Y130.384
G1 X202.583 Y115.218 E.63883
G1 X202.716 Y115.085
G1 X202.716 Y114.551
G1 X202.583 Y114.685
G1 X187.417 Y129.85 E.63883
G1 X187.284 Y129.984
G1 X187.284 Y129.451
G1 X187.417 Y129.317
G1 X202.583 Y114.152 E.63883
G1 X202.716 Y114.018
G1 X202.716 Y113.485
G1 X202.583 Y113.619
G1 X187.417 Y128.784 E.63883
G1 X187.284 Y128.917
G1 X187.284 Y128.384
G1 X187.417 Y128.251
G1 X202.583 Y113.085 E.63883
G1 X202.716 Y112.952
G1 X202.716 Y112.418
G1 X202.583 Y112.552
G1 X187.417 Y127.717 E.63883
G1 X187.284 Y127.851
G1 X187.284 Y127.318
G1 X187.417 Y127.184
G1 X202.583 Y112.019 E.63883
M73 P81 R2
G1 X202.716 Y111.885
G1 X202.716 Y111.352
G1 X202.583 Y111.486
G1 X187.417 Y126.651 E.63883
G1 X187.284 Y126.784
G1 X187.284 Y126.251
G1 X187.417 Y126.118
G1 X202.583 Y110.952 E.63883
G1 X202.716 Y110.819
G1 X202.716 Y110.285
G1 X202.583 Y110.419
G1 X197.317 Y115.685 E.22182
G1 X197.183 Y115.818
G1 X197.273 Y115.195
G1 X197.407 Y115.062
G1 X202.583 Y109.886 E.21804
G1 X202.716 Y109.752
G1 X202.651 Y109.284
G1 X202.518 Y109.417
G1 X197.368 Y114.567 E.21694
G1 X197.234 Y114.701
G1 X197.119 Y114.283
G1 X197.253 Y114.149
G1 X201.985 Y109.417 E.19931
G1 X202.118 Y109.284
G1 X201.585 Y109.284
G1 X201.451 Y109.417
G1 X197.084 Y113.785 E.18397
G1 X196.95 Y113.918
G1 X196.734 Y113.601
G1 X196.868 Y113.467
G1 X200.918 Y109.417 E.17061
G1 X201.052 Y109.284
G1 X200.518 Y109.284
G1 X200.385 Y109.417
G1 X196.602 Y113.2 E.15936
G1 X196.468 Y113.334
G1 X196.163 Y113.106
G1 X196.296 Y112.972
G1 X199.851 Y109.417 E.14975
G1 X199.985 Y109.284
G1 X199.452 Y109.284
G1 X199.318 Y109.417
G1 X195.949 Y112.787 E.14194
G1 X195.815 Y112.921
G1 X195.416 Y112.787
G1 X195.549 Y112.653
G1 X198.785 Y109.417 E.1363
G1 X198.919 Y109.284
G1 X198.385 Y109.284
G1 X198.252 Y109.417
G1 X195.078 Y112.591 E.13367
G1 X194.945 Y112.724
G1 X194.354 Y112.782
G1 X194.487 Y112.648
G1 X197.718 Y109.417 E.13611
G1 X197.852 Y109.284
G1 X197.319 Y109.284
G1 X197.185 Y109.417
G1 X193.458 Y113.144 E.157
; WIPE_START
M204 S8000
G1 X194.165 Y112.437 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.6 I-1.161 J.364 P1  F60000
G1 X195.691 Y117.311 Z3.6
G1 Z3.2
G1 E.4 F1800
G1 F12000
M204 S2000
G1 X187.417 Y125.584 E.34851
G1 X187.284 Y125.718
G1 X187.284 Y125.185
G1 X187.417 Y125.051
G1 X195.063 Y117.406 E.32205
G1 X195.196 Y117.272
G1 X194.701 Y117.234
G1 X194.568 Y117.367
G1 X187.417 Y124.518 E.30121
G1 X187.284 Y124.651
G1 X187.284 Y124.118
G1 X187.417 Y123.984
G1 X194.15 Y117.252 E.28361
G1 X194.284 Y117.118
G1 X193.921 Y116.948
G1 X193.787 Y117.082
G1 X187.417 Y123.451 E.26832
G1 X187.284 Y123.585
G1 X187.284 Y123.052
G1 X187.417 Y122.918
G1 X193.468 Y116.867 E.25487
G1 X193.602 Y116.734
G1 X193.332 Y116.471
G1 X193.198 Y116.604
G1 X187.417 Y122.385 E.2435
G1 X187.284 Y122.518
G1 X187.284 Y121.985
G1 X187.417 Y121.851
G1 X192.972 Y116.297 E.23397
G1 X193.105 Y116.164
G1 X192.921 Y115.814
G1 X192.788 Y115.948
G1 X187.417 Y121.318 E.22623
G1 X187.284 Y121.452
G1 X187.284 Y120.919
G1 X187.417 Y120.785
G1 X192.655 Y115.547 E.22064
G1 X192.789 Y115.413
G1 X192.727 Y114.942
G1 X192.593 Y115.076
G1 X187.417 Y120.252 E.21804
G1 X187.284 Y120.385
G1 X187.284 Y119.852
G1 X187.417 Y119.718
G1 X192.648 Y114.488 E.22035
G1 X192.782 Y114.354
G1 X193.32 Y113.282
G1 X193.187 Y113.416
G1 X187.417 Y119.185 E.24303
G1 X187.284 Y119.319
G1 X187.284 Y118.786
G1 X187.417 Y118.652
G1 X196.652 Y109.417 E.389
G1 X196.786 Y109.284
G1 X196.252 Y109.284
G1 X196.119 Y109.417
G1 X187.417 Y118.119 E.36654
G1 X187.284 Y118.252
G1 X187.284 Y117.719
G1 X187.417 Y117.585
G1 X195.585 Y109.417 E.34408
G1 X195.719 Y109.284
G1 X195.186 Y109.284
G1 X195.052 Y109.417
G1 X187.417 Y117.052 E.32161
G1 X187.284 Y117.186
G1 X187.284 Y116.653
G1 X187.417 Y116.519
G1 X194.519 Y109.417 E.29915
G1 X194.653 Y109.284
G1 X194.119 Y109.284
G1 X193.986 Y109.417
G1 X187.417 Y115.986 E.27669
G1 X187.284 Y116.119
G1 X187.284 Y115.586
G1 X187.417 Y115.452
G1 X193.452 Y109.417 E.25422
G1 X193.586 Y109.284
G1 X193.053 Y109.284
G1 X192.919 Y109.417
G1 X187.417 Y114.919 E.23176
G1 X187.284 Y115.053
G1 X187.284 Y114.52
G1 X187.417 Y114.386
G1 X192.386 Y109.417 E.2093
G1 X192.52 Y109.284
G1 X191.986 Y109.284
G1 X191.853 Y109.417
G1 X187.417 Y113.853 E.18683
G1 X187.284 Y113.986
G1 X187.284 Y113.453
G1 X187.417 Y113.319
G1 X191.319 Y109.417 E.16437
G1 X191.453 Y109.284
G1 X190.92 Y109.284
G1 X190.786 Y109.417
G1 X187.417 Y112.786 E.14191
G1 X187.284 Y112.92
G1 X187.284 Y112.386
G1 X187.417 Y112.253
G1 X190.253 Y109.417 E.11944
G1 X190.386 Y109.284
G1 X189.853 Y109.284
G1 X189.72 Y109.417
G1 X187.417 Y111.72 E.09698
G1 X187.284 Y111.853
G1 X187.284 Y111.32
G1 X187.417 Y111.186
G1 X189.186 Y109.417 E.07452
G1 X189.32 Y109.284
G1 X188.787 Y109.284
G1 X188.653 Y109.417
G1 X187.417 Y110.653 E.05205
G1 X187.284 Y110.787
G1 X187.284 Y110.253
G1 X187.417 Y110.12
G1 X188.12 Y109.417 E.02959
; WIPE_START
M204 S8000
G1 X187.417 Y110.12 E-.37749
G1 X187.413 Y110.124 E-.00251
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.6 I-.765 J.946 P1  F60000
G1 X196.097 Y117.145 Z3.6
G1 Z3.2
G1 E.4 F1800
; FEATURE: Gap infill
; LINE_WIDTH: 0.10669
G1 F15000
M204 S8000
G1 X196.006 Y117.208 E.00056
; LINE_WIDTH: 0.143719
G1 X195.915 Y117.271 E.00088
; LINE_WIDTH: 0.180151
G1 X195.824 Y117.334 E.0012
G1 X195.788 Y117.327 E.0004
; LINE_WIDTH: 0.150783
G1 X195.682 Y117.302 E.00092
; OBJECT_ID: 8
; COOLING_NODE: 0
; WIPE_START
G1 X195.788 Y117.327 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 12
M625
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z3.6 I.052 J-1.216 P1  F60000
G1 X157.584 Y115.684 Z3.6
G1 Z3.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X112.416 Y115.684 E1.45243
G1 X112.416 Y113.516 E.0697
G1 X157.584 Y113.516 E1.45243
G1 X157.584 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X157.991 Y116.091 F60000
G1 F13265.217
M204 S8000
G1 X112.009 Y116.091 E1.47861
G1 X112.009 Y113.109 E.09588
G1 X157.991 Y113.109 E1.47861
G1 X157.991 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X158.398 Y116.498 F60000
G1 F13265.217
M204 S8000
G1 X111.602 Y116.498 E1.50479
G1 X111.602 Y112.702 E.12206
G1 X158.398 Y112.702 E1.50479
G1 X158.398 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X158.79 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F2191
M204 S5000
G1 X111.21 Y116.89 E1.41725
G1 X111.21 Y112.31 E.13642
G1 X158.79 Y112.31 E1.41725
G1 X158.79 Y116.83 E.13464
; WIPE_START
G1 F12000
M204 S8000
M73 P82 R2
G1 X157.79 Y116.831 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.6 I1.175 J-.315 P1  F60000
G1 X157.192 Y114.6 Z3.6
G1 Z3.2
G1 E.4 F1800
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.41999
G1 F12000
M204 S8000
G1 X157.192 Y113.908 E.0206
G1 X136.584 Y113.908 E.61382
G1 X136.584 Y115.292 E.04121
G1 X157.192 Y115.292 E.61382
G1 X157.192 Y114.66 E.01882
M204 S10000
G1 X156.752 Y114.6 F60000
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X156.752 Y114.348 E.01
G1 X137.024 Y114.348 E.78415
G1 X137.024 Y114.852 E.02
G1 X156.752 Y114.852 E.78415
G1 X156.752 Y114.66 E.00762
; WIPE_START
G1 X156.752 Y114.852 E-.07281
G1 X155.943 Y114.852 E-.30719
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.6 I-.021 J-1.217 P1  F60000
G1 X136.192 Y115.191 Z3.6
G1 Z3.2
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F13265.217
M204 S8000
G1 X136.192 Y115.336 E.00464
G1 X135.56 Y115.336 E.02031
G1 X135.954 Y113.864 E.04897
G1 X135.618 Y113.864 E.01083
G1 X130.128 Y115.336 E.18277
G1 X130.452 Y115.336 E.01043
G1 X130.846 Y113.864 E.04897
G1 X125.344 Y115.336 E.18316
G1 X125.738 Y113.864 E.04897
G1 X126.085 Y113.864 E.01118
G1 X120.714 Y115.304 E.17882
G1 X120.714 Y115.069 E.00755
G1 X120.981 Y115.336 E.01213
G1 X120.886 Y115.336 E.00306
M204 S10000
G1 X120.714 Y114.865 F60000
G1 F13265.217
M204 S8000
G1 X120.714 Y114.027 E.02697
G1 X121.319 Y113.864 E.02015
G1 X121.254 Y113.864 E.00209
G1 X122.725 Y115.336 E.0669
G1 X122.789 Y115.336 E.00206
G1 X123.184 Y113.864 E.04897
G1 X122.999 Y113.864 E.00594
G1 X124.47 Y115.336 E.0669
G1 X124.067 Y115.336 E.01297
G1 X124.461 Y113.864 E.04897
G1 X124.743 Y113.864 E.00909
G1 X126.214 Y115.336 E.0669
; WIPE_START
G1 X125.507 Y114.628 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.6 I-.374 J1.158 P1  F60000
G1 X127.694 Y115.336 Z3.6
G1 Z3.2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X126.621 Y115.336 E.03452
G1 X127.015 Y113.864 E.04897
G1 X126.488 Y113.864 E.01695
G1 X127.959 Y115.336 E.0669
G1 X127.898 Y115.336 E.00197
G1 X128.292 Y113.864 E.04897
G1 X128.232 Y113.864 E.00192
G1 X129.704 Y115.336 E.0669
G1 X129.175 Y115.336 E.017
G1 X129.569 Y113.864 E.04897
G1 X128.496 Y113.864 E.03452
; WIPE_START
G1 X129.496 Y113.864 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.6 I0 J1.217 P1  F60000
G1 X129.977 Y113.864 Z3.6
G1 Z3.2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X131.448 Y115.336 E.0669
G1 X131.729 Y115.336 E.00904
G1 X132.123 Y113.864 E.04897
G1 X131.721 Y113.864 E.01292
G1 X133.193 Y115.336 E.0669
G1 X133.006 Y115.336 E.00599
G1 X133.4 Y113.864 E.04897
G1 X133.466 Y113.864 E.00211
G1 X134.937 Y115.336 E.0669
G1 X134.894 Y115.336 E.00139
G1 X136.192 Y114.988 E.04322
G1 X136.192 Y114.846 E.00456
G1 X135.211 Y113.864 E.04463
M204 S10000
G1 X134.677 Y113.864 F60000
G1 F13265.217
M204 S8000
G1 X134.283 Y115.336 E.04897
G1 X133.396 Y115.336 E.02853
; WIPE_START
G1 X134.283 Y115.336 E-.33711
G1 X134.312 Y115.227 E-.04289
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.6 I.143 J-1.209 P1  F60000
G1 X122.795 Y113.864 Z3.6
G1 Z3.2
G1 E.4 F1800
G1 F13265.217
M204 S8000
G1 X121.907 Y113.864 E.02858
G1 X121.512 Y115.336 E.04897
; WIPE_START
G1 X121.771 Y114.37 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.6 I-.653 J-1.027 P1  F60000
G1 X120.322 Y115.292 Z3.6
G1 Z3.2
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F14320.948
M204 S8000
G1 X120.322 Y113.908 E.04121
G1 X112.808 Y113.908 E.22381
G1 X112.808 Y115.292 E.04121
G1 X120.262 Y115.292 E.22202
M204 S10000
G1 X119.882 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F10731.32
M204 S8000
G1 X119.882 Y114.348 E.02
G1 X113.248 Y114.348 E.26368
G1 X113.248 Y114.852 E.02
G1 X119.822 Y114.852 E.2613
; COOLING_NODE: 3
; WIPE_START
G1 X118.822 Y114.852 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.6 I-1.045 J.624 P1  F60000
G1 X154.458 Y174.51 Z3.6
G1 Z3.2
G1 E.4 F1800
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F12000
M204 S5000
G1 X155.542 Y174.51 E.03231
G1 X155.542 Y176.09 E.04706
G1 X154.458 Y176.09 E.03231
G1 X154.458 Y174.57 E.04528
; WIPE_START
M204 S8000
G1 X155.456 Y174.515 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.6 I-1.201 J-.196 P1  F60000
G1 X155.335 Y175.258 Z3.6
G1 Z3.2
G1 E.4 F1800
; FEATURE: Top surface
G1 F12000
M204 S2000
G1 X154.711 Y175.883 E.02629
G1 X154.577 Y176.016
G1 X154.531 Y175.529
G1 X154.665 Y175.395
G1 X155.335 Y174.725 E.02822
; COOLING_NODE: 2
; WIPE_START
M204 S8000
G1 X154.665 Y175.395 E-.36006
G1 X154.628 Y175.432 E-.01994
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.6 I.086 J-1.214 P1  F60000
G1 X141.542 Y174.51 Z3.6
G1 Z3.2
G1 E.4 F1800
; FEATURE: Outer wall
G1 F12000
M204 S5000
G1 X141.542 Y176.09 E.04706
G1 X140.458 Y176.09 E.03231
G1 X140.458 Y174.51 E.04706
G1 X141.482 Y174.51 E.03052
M204 S10000
G1 X141.335 Y175.394 F60000
; FEATURE: Top surface
G1 F12000
M204 S2000
G1 X140.846 Y175.883 E.02059
G1 X140.712 Y176.016
G1 X140.531 Y175.664
G1 X140.665 Y175.53
G1 X141.335 Y174.86 E.02822
; CHANGE_LAYER
; Z_HEIGHT: 3.4
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F12000
M204 S8000
G1 X140.665 Y175.53 E-.36006
G1 X140.628 Y175.568 E-.01994
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 17/27
; update layer progress
M73 L17
M991 S0 P16 ;notify layer change
M106 S73.95
; OBJECT_ID: 8
; COOLING_NODE: 0
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z3.6 I1.214 J-.081 P1  F60000
G1 X136.62 Y115.684 Z3.6
G1 Z3.4
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F3389
M204 S8000
G1 X112.416 Y115.684 E.77829
G1 X112.416 Y113.516 E.0697
G1 X136.62 Y113.516 E.77829
G1 X136.62 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X137.027 Y116.091 F60000
G1 F3389
M204 S8000
G1 X112.009 Y116.091 E.80447
G1 X112.009 Y113.109 E.09588
G1 X137.027 Y113.109 E.80447
G1 X137.027 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X137.434 Y116.498 F60000
G1 F3389
M204 S8000
G1 X111.602 Y116.498 E.83065
G1 X111.602 Y112.702 E.12206
G1 X137.434 Y112.702 E.83065
G1 X137.434 Y116.438 E.12013
; COOLING_NODE: 0
; WIPE_START
G1 F13265.217
G1 X136.434 Y116.44 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.8 I-.024 J1.217 P1  F60000
G1 X158.79 Y116.89 Z3.8
G1 Z3.4
G1 E.4 F1800
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F2046
M204 S5000
G1 X111.21 Y116.89 E1.41725
G1 X111.21 Y112.31 E.13642
G1 X158.79 Y112.31 E1.41725
M73 P83 R2
G1 X158.79 Y116.83 E.13464
; object ids of layer 17 start: 8
M624 AQAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer17 end: 8
M625
; WIPE_START
G1 F12000
M204 S8000
G1 X157.79 Y116.831 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.8 I1.191 J.25 P1  F60000
G1 X158.583 Y113.058 Z3.8
G1 Z3.4
G1 E.4 F1800
; FEATURE: Top surface
G1 F3389
M204 S2000
G1 X158.042 Y112.517 E.02277
G1 X157.908 Y112.384
G1 X157.375 Y112.384
G1 X157.509 Y112.517
G1 X158.583 Y113.591 E.04523
G1 X158.716 Y113.725
G1 X158.716 Y114.258
G1 X158.583 Y114.124
G1 X156.976 Y112.517 E.0677
G1 X156.842 Y112.384
G1 X156.309 Y112.384
G1 X156.442 Y112.517
G1 X158.583 Y114.658 E.09016
G1 X158.716 Y114.791
G1 X158.716 Y115.325
G1 X158.583 Y115.191
G1 X155.909 Y112.517 E.11262
G1 X155.775 Y112.384
G1 X155.242 Y112.384
G1 X155.376 Y112.517
G1 X158.583 Y115.724 E.13509
G1 X158.716 Y115.858
G1 X158.716 Y116.391
G1 X158.583 Y116.257
G1 X154.843 Y112.517 E.15755
G1 X154.709 Y112.384
G1 X154.176 Y112.384
G1 X154.309 Y112.517
G1 X158.474 Y116.683 E.17546
G1 X158.608 Y116.816
G1 X158.075 Y116.816
G1 X157.941 Y116.683
G1 X153.776 Y112.517 E.17546
G1 X153.642 Y112.384
G1 X153.109 Y112.384
G1 X153.243 Y112.517
G1 X157.408 Y116.683 E.17546
G1 X157.542 Y116.816
G1 X157.008 Y116.816
G1 X156.875 Y116.683
G1 X152.709 Y112.517 E.17546
G1 X152.576 Y112.384
G1 X152.043 Y112.384
G1 X152.176 Y112.517
G1 X156.341 Y116.683 E.17546
G1 X156.475 Y116.816
G1 X155.942 Y116.816
G1 X155.808 Y116.683
G1 X151.643 Y112.517 E.17546
G1 X151.509 Y112.384
G1 X150.976 Y112.384
G1 X151.11 Y112.517
G1 X155.275 Y116.683 E.17546
G1 X155.409 Y116.816
G1 X154.875 Y116.816
G1 X154.742 Y116.683
G1 X150.576 Y112.517 E.17546
G1 X150.443 Y112.384
G1 X149.91 Y112.384
G1 X150.043 Y112.517
G1 X154.208 Y116.683 E.17546
G1 X154.342 Y116.816
G1 X153.809 Y116.816
G1 X153.675 Y116.683
G1 X149.51 Y112.517 E.17546
G1 X149.376 Y112.384
G1 X148.843 Y112.384
G1 X148.977 Y112.517
G1 X153.142 Y116.683 E.17546
G1 X153.276 Y116.816
G1 X152.742 Y116.816
G1 X152.609 Y116.683
G1 X148.443 Y112.517 E.17546
G1 X148.31 Y112.384
G1 X147.777 Y112.384
G1 X147.91 Y112.517
G1 X152.075 Y116.683 E.17546
G1 X152.209 Y116.816
G1 X151.676 Y116.816
G1 X151.542 Y116.683
G1 X147.377 Y112.517 E.17546
G1 X147.243 Y112.384
G1 X146.71 Y112.384
G1 X146.844 Y112.517
G1 X151.009 Y116.683 E.17546
G1 X151.143 Y116.816
G1 X150.609 Y116.816
G1 X150.476 Y116.683
G1 X146.31 Y112.517 E.17546
G1 X146.177 Y112.384
G1 X145.643 Y112.384
G1 X145.777 Y112.517
G1 X149.942 Y116.683 E.17546
G1 X150.076 Y116.816
G1 X149.543 Y116.816
G1 X149.409 Y116.683
G1 X145.244 Y112.517 E.17546
G1 X145.11 Y112.384
G1 X144.577 Y112.384
G1 X144.711 Y112.517
G1 X148.876 Y116.683 E.17546
G1 X149.009 Y116.816
G1 X148.476 Y116.816
G1 X148.343 Y116.683
G1 X144.177 Y112.517 E.17546
G1 X144.044 Y112.384
G1 X143.51 Y112.384
G1 X143.644 Y112.517
G1 X147.809 Y116.683 E.17546
G1 X147.943 Y116.816
G1 X147.41 Y116.816
G1 X147.276 Y116.683
G1 X143.111 Y112.517 E.17546
G1 X142.977 Y112.384
G1 X142.444 Y112.384
G1 X142.578 Y112.517
G1 X146.743 Y116.683 E.17546
G1 X146.876 Y116.816
G1 X146.343 Y116.816
G1 X146.21 Y116.683
G1 X142.044 Y112.517 E.17546
G1 X141.911 Y112.384
G1 X141.377 Y112.384
G1 X141.511 Y112.517
G1 X145.676 Y116.683 E.17546
G1 X145.81 Y116.816
G1 X145.277 Y116.816
G1 X145.143 Y116.683
G1 X140.978 Y112.517 E.17546
G1 X140.844 Y112.384
G1 X140.311 Y112.384
G1 X140.445 Y112.517
G1 X144.61 Y116.683 E.17546
G1 X144.743 Y116.816
G1 X144.21 Y116.816
G1 X144.077 Y116.683
G1 X139.911 Y112.517 E.17546
G1 X139.778 Y112.384
G1 X139.244 Y112.384
G1 X139.378 Y112.517
G1 X143.543 Y116.683 E.17546
G1 X143.677 Y116.816
G1 X143.144 Y116.816
G1 X143.01 Y116.683
G1 X138.845 Y112.517 E.17546
G1 X138.711 Y112.384
G1 X138.178 Y112.384
G1 X138.312 Y112.517
G1 X142.477 Y116.683 E.17546
G1 X142.61 Y116.816
G1 X142.077 Y116.816
G1 X141.943 Y116.683
G1 X137.778 Y112.517 E.17546
G1 X137.645 Y112.384
G1 X137.523 Y112.795
G1 X137.656 Y112.929
G1 X141.41 Y116.683 E.15814
G1 X141.544 Y116.816
G1 X141.011 Y116.816
G1 X140.877 Y116.683
G1 X137.656 Y113.462 E.13567
G1 X137.523 Y113.328
G1 X137.523 Y113.861
G1 X137.656 Y113.995
G1 X140.344 Y116.683 E.11321
G1 X140.477 Y116.816
G1 X139.944 Y116.816
G1 X139.81 Y116.683
G1 X137.656 Y114.528 E.09075
G1 X137.523 Y114.395
G1 X137.523 Y114.928
G1 X137.656 Y115.062
G1 X139.277 Y116.683 E.06828
G1 X139.411 Y116.816
G1 X138.878 Y116.816
G1 X138.744 Y116.683
G1 X137.656 Y115.595 E.04582
G1 X137.523 Y115.461
G1 X137.523 Y115.995
G1 X137.656 Y116.128
G1 X138.211 Y116.683 E.02336
; WIPE_START
G1 F12000
M204 S8000
G1 X137.656 Y116.128 E-.29797
G1 X137.523 Y115.995 E-.07182
G1 X137.523 Y115.968 E-.01021
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.8 I.859 J-.862 P1  F60000
G1 X135.411 Y113.864 Z3.8
G1 Z3.4
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F3389
M204 S8000
G1 X136.271 Y114.725 E.03915
G1 X136.271 Y115.113 E.01246
G1 X135.414 Y115.336 E.02849
G1 X135.808 Y113.864 E.04897
G1 X136.164 Y113.864 E.01145
M73 P84 R2
G1 X130.674 Y115.336 E.18277
G1 X130.306 Y115.336 E.01185
G1 X130.7 Y113.864 E.04897
M204 S10000
G1 X130.177 Y113.864 F60000
G1 F3389
M204 S8000
G1 X131.648 Y115.336 E.0669
M204 S10000
G1 X131.583 Y115.336 F60000
G1 F3389
M204 S8000
G1 X131.977 Y113.864 E.04897
G1 X131.921 Y113.864 E.00178
G1 X133.393 Y115.336 E.0669
G1 X132.86 Y115.336 E.01713
G1 X133.254 Y113.864 E.04897
G1 X133.666 Y113.864 E.01325
G1 X135.137 Y115.336 E.0669
G1 X134.137 Y115.336 E.03217
G1 X134.531 Y113.864 E.04897
G1 X133.87 Y113.864 E.02127
; WIPE_START
G1 F13265.217
G1 X134.531 Y113.864 E-.25135
G1 X134.443 Y114.191 E-.12865
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.8 I.145 J-1.208 P1  F60000
G1 X131.718 Y113.864 Z3.8
G1 Z3.4
G1 E.4 F1800
G1 F3389
M204 S8000
G1 X131.398 Y113.864 E.01029
G1 X125.908 Y115.336 E.18277
G1 X125.401 Y115.336 E.01631
; WIPE_START
G1 F13265.217
G1 X125.908 Y115.336 E-.19271
G1 X126.384 Y115.208 E-.1873
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.8 I1.048 J-.618 P1  F60000
G1 X125.591 Y113.864 Z3.8
G1 Z3.4
G1 E.4 F1800
G1 F3389
M204 S8000
G1 X125.197 Y115.336 E.04897
G1 X124.67 Y115.336 E.01696
G1 X123.199 Y113.864 E.0669
G1 X123.037 Y113.864 E.0052
G1 X122.643 Y115.336 E.04897
G1 X122.925 Y115.336 E.00908
G1 X121.454 Y113.864 E.0669
; WIPE_START
G1 F13265.217
G1 X122.161 Y114.572 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.8 I-.843 J-.878 P1  F60000
G1 X121.366 Y115.336 Z3.8
G1 Z3.4
G1 E.4 F1800
G1 F3389
M204 S8000
G1 X121.76 Y113.864 E.04897
G1 X121.866 Y113.864 E.0034
G1 X119.172 Y114.586 E.08968
G1 X119.172 Y115.071 E.01559
G1 X119.436 Y115.336 E.01202
G1 X120.089 Y115.336 E.02098
G1 X120.483 Y113.864 E.04897
G1 X119.71 Y113.864 E.02487
G1 X121.181 Y115.336 E.0669
G1 X126.688 Y113.864 E.1833
G1 X128.159 Y115.336 E.0669
G1 X127.751 Y115.336 E.01311
G1 X128.146 Y113.864 E.04897
G1 X128.432 Y113.864 E.00922
G1 X129.904 Y115.336 E.0669
G1 X129.028 Y115.336 E.02814
G1 X129.423 Y113.864 E.04897
G1 X128.636 Y113.864 E.0253
M204 S10000
G1 X127.942 Y113.864 F60000
G1 F3389
M204 S8000
G1 X126.868 Y113.864 E.03452
G1 X126.474 Y115.336 E.04897
M204 S10000
G1 X126.414 Y115.336 F60000
G1 F3389
M204 S8000
G1 X124.943 Y113.864 E.0669
G1 X124.314 Y113.864 E.02023
G1 X123.92 Y115.336 E.04897
G1 X123.129 Y115.336 E.02544
; WIPE_START
G1 F13265.217
G1 X123.92 Y115.336 E-.30067
G1 X123.974 Y115.134 E-.07933
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z3.8 I-.037 J-1.216 P1  F60000
G1 X118.78 Y115.292 Z3.8
G1 Z3.4
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F3389
M204 S8000
G1 X118.78 Y113.908 E.04121
G1 X112.808 Y113.908 E.17787
G1 X112.808 Y115.292 E.04121
G1 X118.72 Y115.292 E.17608
M204 S10000
G1 X118.34 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F3389
M204 S8000
G1 X118.34 Y114.348 E.02
G1 X113.248 Y114.348 E.20238
G1 X113.248 Y114.852 E.02
G1 X118.28 Y114.852 E.19999
; CHANGE_LAYER
; Z_HEIGHT: 3.6
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F10731.32
G1 X117.28 Y114.852 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 18/27
; update layer progress
M73 L18
M991 S0 P17 ;notify layer change
; OBJECT_ID: 8
; COOLING_NODE: 0
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z3.8 I-.05 J1.216 P1  F60000
G1 X137.584 Y115.684 Z3.8
G1 Z3.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F1747
M204 S8000
G1 X112.416 Y115.684 E.8093
G1 X112.416 Y113.516 E.0697
G1 X137.584 Y113.516 E.8093
G1 X137.584 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X137.991 Y116.091 F60000
G1 F1747
M204 S8000
G1 X112.009 Y116.091 E.83548
G1 X112.009 Y113.109 E.09588
G1 X137.991 Y113.109 E.83548
G1 X137.991 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X138.398 Y116.498 F60000
G1 F1747
M204 S8000
G1 X111.602 Y116.498 E.86166
G1 X111.602 Y112.702 E.12206
G1 X138.398 Y112.702 E.86166
G1 X138.398 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X138.79 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F1747
M204 S5000
G1 X111.21 Y116.89 E.82151
G1 X111.21 Y112.31 E.13642
G1 X138.79 Y112.31 E.82151
M73 P85 R2
G1 X138.79 Y116.83 E.13464
; object ids of layer 18 start: 8
M624 AQAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer18 end: 8
M625
; WIPE_START
G1 F12000
M204 S8000
G1 X137.79 Y116.832 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4 I.989 J-.709 P1  F60000
G1 X135.662 Y113.864 Z4
G1 Z3.6
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F1747
M204 S8000
G1 X135.268 Y115.336 E.04897
G1 X135.337 Y115.336 E.00224
G1 X133.866 Y113.864 E.0669
G1 X134.385 Y113.864 E.01668
G1 X133.99 Y115.336 E.04897
G1 X133.593 Y115.336 E.01279
G1 X132.121 Y113.864 E.0669
G1 X133.108 Y113.864 E.03171
G1 X132.713 Y115.336 E.04897
G1 X133.389 Y115.336 E.02173
; WIPE_START
G1 F13265.217
G1 X132.713 Y115.336 E-.25677
G1 X132.797 Y115.022 E-.12323
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4 I-.381 J-1.156 P1  F60000
G1 X131.848 Y115.336 Z4
G1 Z3.6
G1 E.4 F1800
G1 F1747
M204 S8000
G1 X130.377 Y113.864 E.0669
G1 X130.553 Y113.864 E.00567
G1 X130.159 Y115.336 E.04897
G1 X130.103 Y115.336 E.00179
G1 X128.632 Y113.864 E.0669
G1 X127.999 Y113.864 E.02036
G1 X127.605 Y115.336 E.04897
M204 S10000
G1 X126.851 Y115.336 F60000
G1 F1747
M204 S8000
G1 X126.614 Y115.336 E.0076
G1 X125.143 Y113.864 E.0669
G1 X125.445 Y113.864 E.0097
G1 X125.051 Y115.336 E.04897
G1 X124.87 Y115.336 E.00582
G1 X123.399 Y113.864 E.0669
G1 X124.168 Y113.864 E.02473
G1 X123.774 Y115.336 E.04897
G1 X123.125 Y115.336 E.02085
G1 X121.654 Y113.864 E.0669
M204 S10000
G1 X121.614 Y113.864 F60000
G1 F1747
M204 S8000
G1 X121.22 Y115.336 E.04897
G1 X121.381 Y115.336 E.00519
G1 X119.91 Y113.864 E.0669
G1 X120.337 Y113.864 E.01373
G1 X119.942 Y115.336 E.04897
G1 X119.636 Y115.336 E.00984
G1 X118.165 Y113.864 E.0669
G1 X119.06 Y113.864 E.02876
G1 X118.665 Y115.336 E.04897
G1 X119.433 Y115.336 E.02468
; WIPE_START
G1 F13265.217
G1 X118.665 Y115.336 E-.29161
G1 X118.726 Y115.111 E-.08839
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4 I-.317 J-1.175 P1  F60000
G1 X117.892 Y115.336 Z4
G1 Z3.6
G1 E.4 F1800
G1 F1747
M204 S8000
G1 X116.421 Y113.864 E.0669
M204 S10000
G1 X116.505 Y113.864 F60000
G1 F1747
M204 S8000
G1 X116.111 Y115.336 E.04897
G1 X114.676 Y113.864 E.06608
G1 X115.228 Y113.864 E.01775
G1 X114.834 Y115.336 E.04897
G1 X114.403 Y115.336 E.01387
G1 X112.932 Y113.864 E.0669
G1 X113.951 Y113.864 E.03279
G1 X113.557 Y115.336 E.04897
G1 X112.764 Y115.336 E.02549
G1 X112.764 Y115.172 E.00524
G1 X117.782 Y113.864 E.16675
G1 X117.388 Y115.336 E.04897
; WIPE_START
G1 F13265.217
G1 X117.647 Y114.37 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4 I-.727 J-.976 P1  F60000
G1 X116.351 Y115.336 Z4
G1 Z3.6
G1 E.4 F1800
G1 F1747
M204 S8000
G1 X116.922 Y115.336 E.01837
G1 X122.412 Y113.864 E.18277
G1 X122.891 Y113.864 E.01539
G1 X122.497 Y115.336 E.04897
M204 S10000
G1 X122.085 Y115.336 F60000
G1 F1747
M204 S8000
G1 X121.688 Y115.336 E.01275
G1 X127.178 Y113.864 E.18277
G1 X126.888 Y113.864 E.00934
G1 X128.359 Y115.336 E.0669
G1 X128.882 Y115.336 E.01682
G1 X129.276 Y113.864 E.04897
G1 X130.173 Y113.864 E.02885
; WIPE_START
G1 F13265.217
G1 X129.276 Y113.864 E-.34092
G1 X129.25 Y113.964 E-.03908
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4 I.048 J-1.216 P1  F60000
G1 X126.722 Y113.864 Z4
G1 Z3.6
G1 E.4 F1800
G1 F1747
M204 S8000
G1 X126.328 Y115.336 E.04897
G1 X131.944 Y113.864 E.1867
G1 X131.83 Y113.864 E.00367
G1 X131.436 Y115.336 E.04897
G1 X131.22 Y115.336 E.00694
G1 X136.711 Y113.864 E.18277
G1 X136.939 Y113.864 E.00734
G1 X136.545 Y115.336 E.04897
G1 X135.987 Y115.336 E.01794
G1 X137.236 Y115.001 E.04158
G1 X137.236 Y115.336 E.01076
G1 X137.082 Y115.336 E.00495
G1 X135.611 Y113.864 E.0669
; CHANGE_LAYER
; Z_HEIGHT: 3.8
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F13265.217
G1 X136.318 Y114.572 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 19/27
; update layer progress
M73 L19
M991 S0 P18 ;notify layer change
; OBJECT_ID: 8
; COOLING_NODE: 0
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z4 I-.803 J.914 P1  F60000
G1 X137.584 Y115.684 Z4
G1 Z3.8
G1 E.4 F1800
; FEATURE: Inner wall
G1 F1755
M204 S8000
G1 X112.416 Y115.684 E.8093
G1 X112.416 Y113.516 E.0697
G1 X137.584 Y113.516 E.8093
G1 X137.584 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X137.991 Y116.091 F60000
G1 F1755
M204 S8000
G1 X112.009 Y116.091 E.83548
G1 X112.009 Y113.109 E.09588
G1 X137.991 Y113.109 E.83548
M73 P86 R2
G1 X137.991 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X138.398 Y116.498 F60000
G1 F1755
M204 S8000
G1 X111.602 Y116.498 E.86166
G1 X111.602 Y112.702 E.12206
G1 X138.398 Y112.702 E.86166
G1 X138.398 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X138.79 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F1755
M204 S5000
G1 X111.21 Y116.89 E.82151
G1 X111.21 Y112.31 E.13642
G1 X138.79 Y112.31 E.82151
G1 X138.79 Y116.83 E.13464
; object ids of layer 19 start: 8
M624 AQAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer19 end: 8
M625
; WIPE_START
G1 F12000
M204 S8000
G1 X137.79 Y116.832 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.2 I1.168 J-.343 P1  F60000
G1 X137.236 Y114.944 Z4.2
G1 Z3.8
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F1755
M204 S8000
G1 X137.236 Y113.87 E.03452
G1 X131.767 Y115.336 E.18206
G1 X132.048 Y115.336 E.00904
G1 X130.577 Y113.864 E.0669
G1 X130.407 Y113.864 E.00547
G1 X130.013 Y115.336 E.04897
G1 X130.303 Y115.336 E.00935
G1 X128.832 Y113.864 E.0669
G1 X129.13 Y113.864 E.00956
G1 X128.736 Y115.336 E.04897
G1 X128.559 Y115.336 E.00568
G1 X127.088 Y113.864 E.0669
M204 S10000
G1 X126.576 Y113.864 F60000
G1 F1755
M204 S8000
G1 X126.181 Y115.336 E.04897
G1 X125.273 Y115.336 E.0292
M204 S10000
G1 X124.701 Y115.336 F60000
G1 F1755
M204 S8000
G1 X123.627 Y115.336 E.03452
G1 X124.021 Y113.864 E.04897
G1 X123.599 Y113.864 E.01359
G1 X125.07 Y115.336 E.0669
G1 X124.904 Y115.336 E.00532
G1 X125.299 Y113.864 E.04897
G1 X126.814 Y115.336 E.06792
G1 X127.001 Y115.336 E.00599
G1 X132.491 Y113.864 E.18277
G1 X132.321 Y113.864 E.00545
G1 X133.793 Y115.336 E.0669
G1 X133.844 Y115.336 E.00165
G1 X134.238 Y113.864 E.04897
G1 X134.066 Y113.864 E.00554
G1 X135.537 Y115.336 E.0669
G1 X135.121 Y115.336 E.01338
G1 X135.515 Y113.864 E.04897
G1 X135.811 Y113.864 E.0095
G1 X137.236 Y115.289 E.0648
G1 X137.236 Y115.147 E.00457
G1 X136.398 Y115.336 E.0276
G1 X136.792 Y113.864 E.04897
; WIPE_START
G1 F13265.217
G1 X136.534 Y114.83 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.2 I.414 J-1.144 P1  F60000
G1 X133.862 Y113.864 Z4.2
G1 Z3.8
G1 E.4 F1800
G1 F1755
M204 S8000
G1 X132.961 Y113.864 E.02899
G1 X132.567 Y115.336 E.04897
; WIPE_START
G1 F13265.217
G1 X132.826 Y114.37 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.2 I.492 J-1.113 P1  F60000
G1 X131.684 Y113.864 Z4.2
G1 Z3.8
G1 E.4 F1800
G1 F1755
M204 S8000
G1 X131.29 Y115.336 E.04897
G1 X130.507 Y115.336 E.02517
; WIPE_START
G1 F13265.217
G1 X131.29 Y115.336 E-.29747
G1 X131.346 Y115.126 E-.08253
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.2 I-.066 J-1.215 P1  F60000
G1 X127.459 Y115.336 Z4.2
G1 Z3.8
G1 E.4 F1800
G1 F1755
M204 S8000
G1 X127.853 Y113.864 E.04897
G1 X122.235 Y115.336 E.18675
G1 X122.35 Y115.336 E.00372
G1 X122.744 Y113.864 E.04897
G1 X122.959 Y113.864 E.00689
G1 X117.468 Y115.336 E.18277
G1 X117.242 Y115.336 E.00728
G1 X117.636 Y113.864 E.04897
; WIPE_START
G1 F13265.217
G1 X117.377 Y114.83 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.2 I.434 J1.137 P1  F60000
G1 X119.906 Y113.864 Z4.2
G1 Z3.8
G1 E.4 F1800
G1 F1755
M204 S8000
G1 X118.913 Y113.864 E.03193
G1 X118.519 Y115.336 E.04897
M204 S10000
G1 X118.092 Y115.336 F60000
G1 F1755
M204 S8000
G1 X116.621 Y113.864 E.0669
G1 X116.359 Y113.864 E.00842
G1 X115.965 Y115.336 E.04897
G1 X116.347 Y115.336 E.0123
G1 X114.876 Y113.864 E.0669
G1 X115.082 Y113.864 E.00662
G1 X114.688 Y115.336 E.04897
G1 X114.603 Y115.336 E.00273
G1 X113.132 Y113.864 E.0669
M73 P87 R2
G1 X113.426 Y113.864 E.00947
G1 X112.764 Y114.042 E.02203
G1 X112.764 Y115.319 E.04107
G1 X118.192 Y113.864 E.1807
G1 X118.365 Y113.864 E.00556
G1 X119.836 Y115.336 E.0669
G1 X119.796 Y115.336 E.00129
G1 X120.19 Y113.864 E.04897
G1 X120.11 Y113.864 E.00259
G1 X121.581 Y115.336 E.0669
G1 X121.073 Y115.336 E.01633
G1 X121.467 Y113.864 E.04897
G1 X120.394 Y113.864 E.03452
; WIPE_START
G1 F13265.217
G1 X121.394 Y113.864 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.2 I0 J1.217 P1  F60000
G1 X121.854 Y113.864 Z4.2
G1 Z3.8
G1 E.4 F1800
G1 F1755
M204 S8000
G1 X123.325 Y115.336 E.0669
; WIPE_START
G1 F13265.217
G1 X122.618 Y114.628 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.2 I.116 J-1.211 P1  F60000
G1 X114.673 Y113.864 Z4.2
G1 Z3.8
G1 E.4 F1800
G1 F1755
M204 S8000
G1 X113.805 Y113.864 E.02791
G1 X113.411 Y115.336 E.04897
; CHANGE_LAYER
; Z_HEIGHT: 4
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F13265.217
G1 X113.669 Y114.37 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 20/27
; update layer progress
M73 L20
M991 S0 P19 ;notify layer change
; OBJECT_ID: 8
; COOLING_NODE: 0
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z4.2 I-.067 J1.215 P1  F60000
G1 X137.584 Y115.684 Z4.2
G1 Z4
G1 E.4 F1800
; FEATURE: Inner wall
G1 F1775
M204 S8000
G1 X112.416 Y115.684 E.8093
G1 X112.416 Y113.516 E.0697
G1 X137.584 Y113.516 E.8093
M73 P87 R1
G1 X137.584 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X137.991 Y116.091 F60000
G1 F1775
M204 S8000
G1 X112.009 Y116.091 E.83548
G1 X112.009 Y113.109 E.09588
G1 X137.991 Y113.109 E.83548
G1 X137.991 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X138.398 Y116.498 F60000
G1 F1775
M204 S8000
G1 X111.602 Y116.498 E.86166
G1 X111.602 Y112.702 E.12206
G1 X138.398 Y112.702 E.86166
G1 X138.398 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X138.79 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F1775
M204 S5000
G1 X111.21 Y116.89 E.82151
G1 X111.21 Y112.31 E.13642
G1 X138.79 Y112.31 E.82151
G1 X138.79 Y116.83 E.13464
; object ids of layer 20 start: 8
M624 AQAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer20 end: 8
M625
; WIPE_START
G1 F12000
M204 S8000
M73 P88 R1
G1 X137.79 Y116.832 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.4 I.468 J-1.123 P1  F60000
G1 X134.196 Y115.336 Z4.4
G1 Z4
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F1775
M204 S8000
G1 X134.975 Y115.336 E.02504
G1 X135.369 Y113.864 E.04897
G1 X134.47 Y113.864 E.02892
; WIPE_START
G1 F13265.217
G1 X135.369 Y113.864 E-.34174
G1 X135.343 Y113.962 E-.03826
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.4 I.042 J-1.216 P1  F60000
G1 X132.521 Y113.864 Z4.4
G1 Z4
G1 E.4 F1800
G1 F1775
M204 S8000
G1 X133.993 Y115.336 E.0669
G1 X133.698 Y115.336 E.00948
G1 X134.092 Y113.864 E.04897
G1 X134.266 Y113.864 E.0056
G1 X135.737 Y115.336 E.0669
G1 X136.252 Y115.336 E.01655
G1 X136.646 Y113.864 E.04897
G1 X136.011 Y113.864 E.02043
G1 X137.236 Y115.089 E.05571
G1 X137.236 Y114.017 E.0345
G1 X132.248 Y115.336 E.16589
G1 X130.777 Y113.864 E.0669
G1 X130.261 Y113.864 E.01661
G1 X129.866 Y115.336 E.04897
G1 X130.503 Y115.336 E.02049
G1 X128.983 Y113.864 E.06802
G1 X128.589 Y115.336 E.04897
M204 S10000
G1 X128.759 Y115.336 F60000
G1 F1775
M204 S8000
G1 X127.288 Y113.864 E.0669
M204 S10000
G1 X127.706 Y113.864 F60000
G1 F1775
M204 S8000
G1 X127.312 Y115.336 E.04897
G1 X127.547 Y115.336 E.00755
G1 X133.037 Y113.864 E.18277
G1 X132.815 Y113.864 E.00716
G1 X132.421 Y115.336 E.04897
G1 X132.71 Y115.336 E.0093
M204 S10000
G1 X132.044 Y115.336 F60000
G1 F1775
M204 S8000
G1 X131.143 Y115.336 E.02897
G1 X131.538 Y113.864 E.04897
G1 X130.98 Y113.864 E.01791
; WIPE_START
G1 F13265.217
G1 X131.538 Y113.864 E-.21171
G1 X131.423 Y114.292 E-.16829
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.4 I.194 J-1.201 P1  F60000
G1 X128.78 Y113.864 Z4.4
G1 Z4
G1 E.4 F1800
G1 F1775
M204 S8000
G1 X128.271 Y113.864 E.01636
G1 X122.781 Y115.336 E.18277
G1 X122.407 Y115.336 E.01201
; WIPE_START
G1 F13265.217
G1 X122.781 Y115.336 E-.14197
G1 X123.386 Y115.173 E-.23803
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.4 I-.063 J-1.215 P1  F60000
G1 X120.24 Y115.336 Z4.4
G1 Z4
G1 E.4 F1800
G1 F1775
M204 S8000
G1 X120.927 Y115.336 E.02209
G1 X121.321 Y113.864 E.04897
G1 X122.054 Y113.864 E.02358
G1 X123.525 Y115.336 E.0669
M204 S10000
G1 X123.481 Y115.336 F60000
G1 F1775
M204 S8000
G1 X123.875 Y113.864 E.04897
G1 X123.799 Y113.864 E.00245
G1 X125.27 Y115.336 E.0669
G1 X124.758 Y115.336 E.01646
G1 X125.152 Y113.864 E.04897
G1 X125.543 Y113.864 E.01258
G1 X127.014 Y115.336 E.0669
G1 X126.035 Y115.336 E.03149
G1 X126.429 Y113.864 E.04897
G1 X125.747 Y113.864 E.02194
; WIPE_START
G1 F13265.217
G1 X126.429 Y113.864 E-.2593
G1 X126.347 Y114.171 E-.1207
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.4 I-.155 J-1.207 P1  F60000
G1 X117.299 Y115.336 Z4.4
G1 Z4
G1 E.4 F1800
G1 F1775
M204 S8000
G1 X118.015 Y115.336 E.02302
G1 X123.505 Y113.864 E.18277
G1 X123.108 Y113.864 E.01275
M204 S10000
G1 X122.598 Y113.864 F60000
G1 F1775
M204 S8000
G1 X122.204 Y115.336 E.04897
G1 X121.781 Y115.336 E.0136
G1 X120.31 Y113.864 E.0669
G1 X120.044 Y113.864 E.00855
G1 X119.65 Y115.336 E.04897
G1 X120.036 Y115.336 E.01243
G1 X118.565 Y113.864 E.0669
G1 X118.342 Y113.864 E.00717
M204 S10000
G1 X117.49 Y113.864 F60000
G1 F1775
M204 S8000
G1 X117.095 Y115.336 E.04897
G1 X116.547 Y115.336 E.01763
G1 X115.076 Y113.864 E.0669
G1 X114.935 Y113.864 E.00452
G1 X114.541 Y115.336 E.04897
G1 X114.803 Y115.336 E.00841
G1 X113.332 Y113.864 E.0669
G1 X112.764 Y113.864 E.01824
G1 X112.764 Y113.985 E.00387
; WIPE_START
G1 F13265.217
G1 X112.764 Y113.864 E-.04568
G1 X113.332 Y113.864 E-.21553
G1 X113.553 Y114.086 E-.1188
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.4 I-1.007 J-.684 P1  F60000
G1 X112.764 Y115.245 Z4.4
G1 Z4
G1 E.4 F1800
G1 F1775
M204 S8000
G1 X112.764 Y115.336 E.0029
G1 X113.058 Y115.336 E.00945
G1 X112.764 Y115.042 E.01336
G1 X112.764 Y114.188 E.02745
G1 X113.973 Y113.864 E.04022
G1 X113.658 Y113.864 E.0101
G1 X113.249 Y115.336 E.04911
G1 X118.767 Y113.864 E.18364
G1 X118.373 Y115.336 E.04897
G1 X118.292 Y115.336 E.0026
G1 X116.821 Y113.864 E.0669
G1 X116.213 Y113.864 E.01955
G1 X115.818 Y115.336 E.04897
G1 X115.006 Y115.336 E.02612
; CHANGE_LAYER
; Z_HEIGHT: 4.2
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F13265.217
G1 X115.818 Y115.336 E-.30862
G1 X115.867 Y115.154 E-.07138
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 21/27
; update layer progress
M73 L21
M991 S0 P20 ;notify layer change
; OBJECT_ID: 8
; COOLING_NODE: 0
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z4.4 I-.03 J1.217 P1  F60000
G1 X137.584 Y115.684 Z4.4
G1 Z4.2
G1 E.4 F1800
; FEATURE: Inner wall
G1 F1750
M204 S8000
G1 X112.416 Y115.684 E.8093
G1 X112.416 Y113.516 E.0697
G1 X137.584 Y113.516 E.8093
G1 X137.584 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X137.991 Y116.091 F60000
G1 F1750
M204 S8000
G1 X112.009 Y116.091 E.83548
G1 X112.009 Y113.109 E.09588
G1 X137.991 Y113.109 E.83548
G1 X137.991 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X138.398 Y116.498 F60000
G1 F1750
M204 S8000
G1 X111.602 Y116.498 E.86166
G1 X111.602 Y112.702 E.12206
G1 X138.398 Y112.702 E.86166
M73 P89 R1
G1 X138.398 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X138.79 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F1747
M204 S5000
G1 X111.21 Y116.89 E.82151
G1 X111.21 Y112.31 E.13642
G1 X138.79 Y112.31 E.82151
G1 X138.79 Y116.83 E.13464
; object ids of layer 21 start: 8
M624 AQAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer21 end: 8
M625
; WIPE_START
G1 F12000
M204 S8000
G1 X137.79 Y116.832 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.6 I.405 J-1.148 P1  F60000
G1 X133.551 Y115.336 Z4.6
G1 Z4.2
G1 E.4 F1800
; FEATURE: Sparse infill
; LINE_WIDTH: 0.45
G1 F1750
M204 S8000
G1 X133.945 Y113.864 E.04897
G1 X133.584 Y113.864 E.01163
G1 X128.094 Y115.336 E.18277
G1 X128.443 Y115.336 E.01123
G1 X128.817 Y113.864 E.04881
G1 X123.327 Y115.336 E.18277
G1 X123.729 Y113.864 E.04903
G1 X123.795 Y113.864 E.00214
M204 S10000
G1 X124.255 Y113.864 F60000
G1 F1750
M204 S8000
G1 X125.006 Y113.864 E.02415
G1 X124.612 Y115.336 E.04897
G1 X125.266 Y115.336 E.02106
; WIPE_START
G1 F13265.217
G1 X124.612 Y115.336 E-.24881
G1 X124.701 Y115.002 E-.13119
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.6 I-.394 J-1.152 P1  F60000
G1 X123.725 Y115.336 Z4.6
G1 Z4.2
G1 E.4 F1800
G1 F1750
M204 S8000
G1 X122.254 Y113.864 E.0669
G1 X122.452 Y113.864 E.00634
G1 X122.057 Y115.336 E.04897
G1 X121.981 Y115.336 E.00246
G1 X120.51 Y113.864 E.0669
G1 X121.175 Y113.864 E.02138
G1 X120.78 Y115.336 E.04897
G1 X120.236 Y115.336 E.01749
G1 X118.765 Y113.864 E.0669
M204 S10000
G1 X118.62 Y113.864 F60000
G1 F1750
M204 S8000
G1 X118.226 Y115.336 E.04897
G1 X117.153 Y115.336 E.03452
M204 S10000
G1 X116.544 Y115.336 F60000
G1 F1750
M204 S8000
G1 X115.672 Y115.336 E.02803
G1 X116.066 Y113.864 E.04897
G1 X115.276 Y113.864 E.0254
G1 X116.747 Y115.336 E.0669
G1 X116.949 Y115.336 E.00649
G1 X117.343 Y113.864 E.04897
G1 X117.021 Y113.864 E.01037
G1 X118.492 Y115.336 E.0669
G1 X124.051 Y113.864 E.18493
G1 X123.999 Y113.864 E.00169
G1 X125.47 Y115.336 E.0669
G1 X125.889 Y115.336 E.01347
G1 X126.283 Y113.864 E.04897
G1 X125.743 Y113.864 E.01735
G1 X127.214 Y115.336 E.0669
G1 X127.166 Y115.336 E.00157
G1 X127.56 Y113.864 E.04897
; WIPE_START
G1 F13265.217
G1 X127.301 Y114.83 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.6 I.93 J-.785 P1  F60000
G1 X126.486 Y113.864 Z4.6
G1 Z4.2
G1 E.4 F1800
G1 F1750
M204 S8000
G1 X127.488 Y113.864 E.0322
G1 X128.959 Y115.336 E.0669
; WIPE_START
G1 F13265.217
G1 X128.252 Y114.628 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.6 I-.365 J1.161 P1  F60000
G1 X130.5 Y115.336 Z4.6
G1 Z4.2
G1 E.4 F1800
G1 F1750
M204 S8000
G1 X129.72 Y115.336 E.02508
G1 X130.114 Y113.864 E.04897
G1 X129.232 Y113.864 E.02835
G1 X130.703 Y115.336 E.0669
G1 X130.997 Y115.336 E.00944
G1 X131.391 Y113.864 E.04897
G1 X130.977 Y113.864 E.01332
G1 X132.448 Y115.336 E.0669
G1 X132.274 Y115.336 E.00559
G1 X132.668 Y113.864 E.04897
M204 S10000
G1 X132.721 Y113.864 F60000
G1 F1750
M204 S8000
G1 X134.193 Y115.336 E.0669
G1 X134.828 Y115.336 E.02044
G1 X135.222 Y113.864 E.04897
G1 X134.466 Y113.864 E.02432
G1 X135.937 Y115.336 E.0669
G1 X136.105 Y115.336 E.00541
G1 X136.5 Y113.864 E.04897
G1 X136.211 Y113.864 E.00929
G1 X137.236 Y114.889 E.04661
G1 X137.236 Y114.163 E.02336
G1 X132.86 Y115.336 E.14568
G1 X132.652 Y115.336 E.00669
; WIPE_START
G1 F13265.217
G1 X132.86 Y115.336 E-.07908
G1 X133.625 Y115.131 E-.30092
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.6 I-.018 J-1.217 P1  F60000
G1 X119.503 Y115.336 Z4.6
G1 Z4.2
G1 E.4 F1800
G1 F1750
M204 S8000
G1 X119.897 Y113.864 E.04897
G1 X119.285 Y113.864 E.01969
G1 X113.795 Y115.336 E.18277
G1 X113.462 Y115.336 E.01072
M204 S10000
G1 X114.395 Y115.336 F60000
G1 F1750
M204 S8000
G1 X114.789 Y113.864 E.04897
G1 X114.519 Y113.864 E.00868
G1 X112.764 Y114.335 E.05841
G1 X112.764 Y114.842 E.01631
G1 X113.258 Y115.336 E.02245
G1 X113.118 Y115.336 E.00451
G1 X113.512 Y113.864 E.04897
M204 S10000
G1 X113.532 Y113.864 F60000
G1 F1750
M204 S8000
G1 X115.003 Y115.336 E.0669
; CHANGE_LAYER
; Z_HEIGHT: 4.4
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F13265.217
G1 X114.296 Y114.628 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 22/27
; update layer progress
M73 L22
M991 S0 P21 ;notify layer change
; OBJECT_ID: 8
; COOLING_NODE: 0
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z4.6 I-.055 J1.216 P1  F60000
G1 X137.584 Y115.684 Z4.6
G1 Z4.4
G1 E.4 F1800
; FEATURE: Inner wall
G1 F1702
M204 S8000
G1 X112.416 Y115.684 E.8093
G1 X112.416 Y113.516 E.0697
G1 X137.584 Y113.516 E.8093
M73 P90 R1
G1 X137.584 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X137.991 Y116.091 F60000
G1 F1702
M204 S8000
G1 X112.009 Y116.091 E.83548
G1 X112.009 Y113.109 E.09588
G1 X137.991 Y113.109 E.83548
G1 X137.991 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X138.398 Y116.498 F60000
G1 F1702
M204 S8000
G1 X111.602 Y116.498 E.86166
G1 X111.602 Y112.702 E.12206
G1 X138.398 Y112.702 E.86166
G1 X138.398 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X138.79 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F1702
M204 S5000
G1 X111.21 Y116.89 E.82151
G1 X111.21 Y112.31 E.13642
G1 X138.79 Y112.31 E.82151
G1 X138.79 Y116.83 E.13464
; object ids of layer 22 start: 8
M624 AQAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer22 end: 8
M625
; WIPE_START
G1 F12000
M204 S8000
G1 X137.79 Y116.832 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z4.8 I1.175 J-.315 P1  F60000
G1 X137.192 Y114.6 Z4.8
G1 Z4.4
G1 E.4 F1800
; FEATURE: Floating vertical shell
; LINE_WIDTH: 0.41999
G1 F1702
M204 S8000
G1 X137.192 Y113.908 E.0206
G1 X112.808 Y113.908 E.72628
G1 X112.808 Y115.292 E.04121
G1 X137.192 Y115.292 E.72628
M73 P91 R1
G1 X137.192 Y114.66 E.01882
M204 S10000
G1 X136.752 Y114.6 F60000
; LINE_WIDTH: 0.54612
G1 F1702
M204 S8000
G1 X136.752 Y114.348 E.01
G1 X113.248 Y114.348 E.93423
G1 X113.248 Y114.852 E.02
G1 X136.752 Y114.852 E.93423
G1 X136.752 Y114.66 E.00762
; CHANGE_LAYER
; Z_HEIGHT: 4.6
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F10731.32
G1 X136.752 Y114.852 E-.07281
G1 X135.943 Y114.852 E-.30719
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 23/27
; update layer progress
M73 L23
M991 S0 P22 ;notify layer change
; OBJECT_ID: 8
; COOLING_NODE: 0
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z4.8 I-.551 J1.085 P1  F60000
G1 X137.584 Y115.684 Z4.8
G1 Z4.6
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F1702
M204 S8000
G1 X112.416 Y115.684 E.8093
G1 X112.416 Y113.516 E.0697
G1 X137.584 Y113.516 E.8093
G1 X137.584 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X137.991 Y116.091 F60000
G1 F1702
M204 S8000
G1 X112.009 Y116.091 E.83548
G1 X112.009 Y113.109 E.09588
G1 X137.991 Y113.109 E.83548
G1 X137.991 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X138.398 Y116.498 F60000
G1 F1702
M204 S8000
G1 X111.602 Y116.498 E.86166
G1 X111.602 Y112.702 E.12206
G1 X138.398 Y112.702 E.86166
G1 X138.398 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X138.79 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F1702
M204 S5000
G1 X111.21 Y116.89 E.82151
G1 X111.21 Y112.31 E.13642
G1 X138.79 Y112.31 E.82151
M73 P92 R1
G1 X138.79 Y116.83 E.13464
; object ids of layer 23 start: 8
M624 AQAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer23 end: 8
M625
; WIPE_START
G1 F12000
M204 S8000
G1 X137.79 Y116.832 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z5 I1.134 J-.441 P1  F60000
G1 X137.192 Y115.292 Z5
G1 Z4.6
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F1702
M204 S8000
G1 X137.192 Y113.908 E.04121
G1 X112.808 Y113.908 E.72628
G1 X112.808 Y115.292 E.04121
G1 X137.132 Y115.292 E.72449
M204 S10000
G1 X136.752 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F1702
M204 S8000
G1 X136.752 Y114.348 E.02
G1 X113.248 Y114.348 E.93423
G1 X113.248 Y114.852 E.02
G1 X136.692 Y114.852 E.93185
; CHANGE_LAYER
; Z_HEIGHT: 4.8
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F10731.32
G1 X135.692 Y114.852 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 24/27
; update layer progress
M73 L24
M991 S0 P23 ;notify layer change
; OBJECT_ID: 8
; COOLING_NODE: 0
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z5 I-.49 J1.114 P1  F60000
G1 X137.584 Y115.684 Z5
G1 Z4.8
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F1703
M204 S8000
G1 X112.416 Y115.684 E.8093
G1 X112.416 Y113.516 E.0697
G1 X137.584 Y113.516 E.8093
G1 X137.584 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X137.991 Y116.091 F60000
G1 F1703
M204 S8000
G1 X112.009 Y116.091 E.83548
G1 X112.009 Y113.109 E.09588
G1 X137.991 Y113.109 E.83548
G1 X137.991 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X138.398 Y116.498 F60000
M73 P93 R1
G1 F1703
M204 S8000
G1 X111.602 Y116.498 E.86166
G1 X111.602 Y112.702 E.12206
G1 X138.398 Y112.702 E.86166
G1 X138.398 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X138.79 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F1703
M204 S5000
G1 X111.21 Y116.89 E.82151
G1 X111.21 Y112.31 E.13642
G1 X138.79 Y112.31 E.82151
G1 X138.79 Y116.83 E.13464
; object ids of layer 24 start: 8
M624 AQAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer24 end: 8
M625
; WIPE_START
G1 F12000
M204 S8000
G1 X137.79 Y116.832 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z5.2 I1.134 J-.441 P1  F60000
G1 X137.192 Y115.292 Z5.2
G1 Z4.8
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F1703
M204 S8000
G1 X137.192 Y113.908 E.04121
G1 X112.808 Y113.908 E.72628
G1 X112.808 Y115.292 E.04121
G1 X137.132 Y115.292 E.72449
M204 S10000
M73 P93 R0
G1 X136.752 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F1703
M204 S8000
G1 X136.752 Y114.348 E.02
G1 X113.248 Y114.348 E.93423
G1 X113.248 Y114.852 E.02
G1 X136.692 Y114.852 E.93185
; CHANGE_LAYER
; Z_HEIGHT: 5
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F10731.32
G1 X135.692 Y114.852 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 25/27
; update layer progress
M73 L25
M991 S0 P24 ;notify layer change
; OBJECT_ID: 8
; COOLING_NODE: 0
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z5.2 I-.49 J1.114 P1  F60000
G1 X137.584 Y115.684 Z5.2
G1 Z5
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F1703
M204 S8000
G1 X112.416 Y115.684 E.8093
G1 X112.416 Y113.516 E.0697
G1 X137.584 Y113.516 E.8093
M73 P94 R0
G1 X137.584 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X137.991 Y116.091 F60000
G1 F1703
M204 S8000
G1 X112.009 Y116.091 E.83548
G1 X112.009 Y113.109 E.09588
G1 X137.991 Y113.109 E.83548
G1 X137.991 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X138.398 Y116.498 F60000
G1 F1703
M204 S8000
G1 X111.602 Y116.498 E.86166
G1 X111.602 Y112.702 E.12206
G1 X138.398 Y112.702 E.86166
G1 X138.398 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X138.79 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F1703
M204 S5000
G1 X111.21 Y116.89 E.82151
G1 X111.21 Y112.31 E.13642
G1 X138.79 Y112.31 E.82151
G1 X138.79 Y116.83 E.13464
; object ids of layer 25 start: 8
M624 AQAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer25 end: 8
M625
; WIPE_START
G1 F12000
M204 S8000
G1 X137.79 Y116.832 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z5.4 I1.134 J-.441 P1  F60000
G1 X137.192 Y115.292 Z5.4
G1 Z5
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F1703
M204 S8000
G1 X137.192 Y113.908 E.04121
G1 X112.808 Y113.908 E.72628
G1 X112.808 Y115.292 E.04121
G1 X137.132 Y115.292 E.72449
M204 S10000
G1 X136.752 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F1703
M204 S8000
M73 P95 R0
G1 X136.752 Y114.348 E.02
G1 X113.248 Y114.348 E.93423
G1 X113.248 Y114.852 E.02
G1 X136.692 Y114.852 E.93185
; CHANGE_LAYER
; Z_HEIGHT: 5.2
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F10731.32
G1 X135.692 Y114.852 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 26/27
; update layer progress
M73 L26
M991 S0 P25 ;notify layer change
; OBJECT_ID: 8
; COOLING_NODE: 0
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z5.4 I-.49 J1.114 P1  F60000
G1 X137.584 Y115.684 Z5.4
G1 Z5.2
G1 E.4 F1800
; FEATURE: Inner wall
; LINE_WIDTH: 0.45
G1 F1703
M204 S8000
G1 X112.416 Y115.684 E.8093
G1 X112.416 Y113.516 E.0697
G1 X137.584 Y113.516 E.8093
G1 X137.584 Y115.624 E.06777
; COOLING_NODE: 0
M204 S10000
G1 X137.991 Y116.091 F60000
G1 F1703
M204 S8000
G1 X112.009 Y116.091 E.83548
G1 X112.009 Y113.109 E.09588
G1 X137.991 Y113.109 E.83548
G1 X137.991 Y116.031 E.09395
; COOLING_NODE: 0
M204 S10000
G1 X138.398 Y116.498 F60000
G1 F1703
M204 S8000
G1 X111.602 Y116.498 E.86166
G1 X111.602 Y112.702 E.12206
G1 X138.398 Y112.702 E.86166
G1 X138.398 Y116.438 E.12013
; COOLING_NODE: 0
M204 S250
G1 X138.79 Y116.89 F60000
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F1703
M204 S5000
G1 X111.21 Y116.89 E.82151
G1 X111.21 Y112.31 E.13642
G1 X138.79 Y112.31 E.82151
M73 P96 R0
G1 X138.79 Y116.83 E.13464
; object ids of layer 26 start: 8
M624 AQAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer26 end: 8
M625
; WIPE_START
G1 F12000
M204 S8000
G1 X137.79 Y116.832 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z5.6 I1.134 J-.441 P1  F60000
G1 X137.192 Y115.292 Z5.6
G1 Z5.2
G1 E.4 F1800
; FEATURE: Internal solid infill
; LINE_WIDTH: 0.41999
G1 F1703
M204 S8000
G1 X137.192 Y113.908 E.04121
G1 X112.808 Y113.908 E.72628
G1 X112.808 Y115.292 E.04121
G1 X137.132 Y115.292 E.72449
M204 S10000
G1 X136.752 Y114.852 F60000
; LINE_WIDTH: 0.54612
G1 F1703
M204 S8000
G1 X136.752 Y114.348 E.02
G1 X113.248 Y114.348 E.93423
G1 X113.248 Y114.852 E.02
G1 X136.692 Y114.852 E.93185
; CHANGE_LAYER
; Z_HEIGHT: 5.4
; LAYER_HEIGHT: 0.2
; WIPE_START
G1 F10731.32
G1 X135.692 Y114.852 E-.38
; WIPE_END
G1 E-.02 F1800
; stop printing object, unique label id: 8
M625
; layer num/total_layer_count: 27/27
; update layer progress
M73 L27
M991 S0 P26 ;notify layer change
; OBJECT_ID: 8
; COOLING_NODE: 0
; start printing object, unique label id: 8
M624 AQAAAAAAAAA=
M204 S10000
G17
G3 Z5.6 I-.669 J1.017 P1  F60000
G1 X138.79 Y116.89 Z5.6
G1 Z5.4
G1 E.4 F1800
; FEATURE: Outer wall
; LINE_WIDTH: 0.42
G1 F1703
M204 S5000
G1 X111.21 Y116.89 E.82151
G1 X111.21 Y112.31 E.13642
G1 X138.79 Y112.31 E.82151
G1 X138.79 Y116.83 E.13464
; object ids of layer 27 start: 8
M624 AQAAAAAAAAA=
;========Date 20250206========
M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
 ; timelapse without wipe tower
M971 S11 C10 O0 T3000

M623

; object ids of this layer27 end: 8
M625
; WIPE_START
G1 F12000
M204 S8000
G1 X137.79 Y116.832 E-.38
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z5.8 I1.217 J-.003 P1  F60000
G1 X137.778 Y112.517 Z5.8
G1 Z5.4
G1 E.4 F1800
; FEATURE: Top surface
G1 F2176
M204 S2000
G1 X138.583 Y113.322 E.03388
G1 X138.716 Y113.455
G1 X138.716 Y113.989
G1 X138.583 Y113.855
G1 X137.245 Y112.517 E.05635
G1 X137.111 Y112.384
G1 X136.578 Y112.384
G1 X136.712 Y112.517
G1 X138.583 Y114.388 E.07881
G1 X138.716 Y114.522
G1 X138.716 Y115.055
G1 X138.583 Y114.922
G1 X136.178 Y112.517 E.10127
G1 X136.045 Y112.384
G1 X135.512 Y112.384
G1 X135.645 Y112.517
G1 X138.583 Y115.455 E.12374
G1 X138.716 Y115.588
M73 P97 R0
G1 X138.716 Y116.122
G1 X138.583 Y115.988
G1 X135.112 Y112.517 E.1462
G1 X134.978 Y112.384
G1 X134.445 Y112.384
G1 X134.579 Y112.517
G1 X138.583 Y116.521 E.16866
G1 X138.716 Y116.655
G1 X138.344 Y116.816
G1 X138.211 Y116.683
G1 X134.045 Y112.517 E.17546
G1 X133.912 Y112.384
G1 X133.379 Y112.384
G1 X133.512 Y112.517
G1 X137.677 Y116.683 E.17546
G1 X137.811 Y116.816
G1 X137.278 Y116.816
G1 X137.144 Y116.683
G1 X132.979 Y112.517 E.17546
G1 X132.845 Y112.384
G1 X132.312 Y112.384
G1 X132.446 Y112.517
G1 X136.611 Y116.683 E.17546
G1 X136.745 Y116.816
G1 X136.211 Y116.816
G1 X136.078 Y116.683
G1 X131.912 Y112.517 E.17546
G1 X131.779 Y112.384
G1 X131.246 Y112.384
G1 X131.379 Y112.517
G1 X135.544 Y116.683 E.17546
G1 X135.678 Y116.816
G1 X135.145 Y116.816
G1 X135.011 Y116.683
G1 X130.846 Y112.517 E.17546
G1 X130.712 Y112.384
G1 X130.179 Y112.384
G1 X130.313 Y112.517
G1 X134.478 Y116.683 E.17546
G1 X134.612 Y116.816
G1 X134.078 Y116.816
G1 X133.945 Y116.683
G1 X129.779 Y112.517 E.17546
G1 X129.646 Y112.384
G1 X129.112 Y112.384
G1 X129.246 Y112.517
G1 X133.411 Y116.683 E.17546
G1 X133.545 Y116.816
G1 X133.012 Y116.816
G1 X132.878 Y116.683
G1 X128.713 Y112.517 E.17546
G1 X128.579 Y112.384
G1 X128.046 Y112.384
G1 X128.18 Y112.517
G1 X132.345 Y116.683 E.17546
G1 X132.479 Y116.816
G1 X131.945 Y116.816
G1 X131.812 Y116.683
G1 X127.646 Y112.517 E.17546
G1 X127.513 Y112.384
G1 X126.979 Y112.384
G1 X127.113 Y112.517
G1 X131.278 Y116.683 E.17546
G1 X131.412 Y116.816
G1 X130.879 Y116.816
G1 X130.745 Y116.683
G1 X126.58 Y112.517 E.17546
G1 X126.446 Y112.384
G1 X125.913 Y112.384
G1 X126.047 Y112.517
G1 X130.212 Y116.683 E.17546
G1 X130.345 Y116.816
G1 X129.812 Y116.816
G1 X129.679 Y116.683
G1 X125.513 Y112.517 E.17546
G1 X125.38 Y112.384
G1 X124.846 Y112.384
G1 X124.98 Y112.517
G1 X129.145 Y116.683 E.17546
G1 X129.279 Y116.816
G1 X128.746 Y116.816
G1 X128.612 Y116.683
G1 X124.447 Y112.517 E.17546
G1 X124.313 Y112.384
G1 X123.78 Y112.384
G1 X123.914 Y112.517
G1 X128.079 Y116.683 E.17546
G1 X128.212 Y116.816
G1 X127.679 Y116.816
G1 X127.546 Y116.683
G1 X123.38 Y112.517 E.17546
G1 X123.247 Y112.384
G1 X122.713 Y112.384
G1 X122.847 Y112.517
G1 X127.012 Y116.683 E.17546
G1 X127.146 Y116.816
G1 X126.613 Y116.816
G1 X126.479 Y116.683
G1 X122.314 Y112.517 E.17546
G1 X122.18 Y112.384
G1 X121.647 Y112.384
G1 X121.781 Y112.517
G1 X125.946 Y116.683 E.17546
G1 X126.079 Y116.816
G1 X125.546 Y116.816
G1 X125.413 Y116.683
G1 X121.247 Y112.517 E.17546
G1 X121.114 Y112.384
G1 X120.58 Y112.384
G1 X120.714 Y112.517
G1 X124.879 Y116.683 E.17546
G1 X125.013 Y116.816
G1 X124.48 Y116.816
G1 X124.346 Y116.683
G1 X120.181 Y112.517 E.17546
G1 X120.047 Y112.384
G1 X119.514 Y112.384
G1 X119.647 Y112.517
G1 X123.813 Y116.683 E.17546
G1 X123.946 Y116.816
G1 X123.413 Y116.816
G1 X123.279 Y116.683
G1 X119.114 Y112.517 E.17546
G1 X118.981 Y112.384
G1 X118.447 Y112.384
G1 X118.581 Y112.517
G1 X122.746 Y116.683 E.17546
G1 X122.88 Y116.816
G1 X122.347 Y116.816
G1 X122.213 Y116.683
G1 X118.048 Y112.517 E.17546
G1 X117.914 Y112.384
G1 X117.381 Y112.384
G1 X117.514 Y112.517
G1 X121.68 Y116.683 E.17546
G1 X121.813 Y116.816
G1 X121.28 Y116.816
M73 P98 R0
G1 X121.146 Y116.683
G1 X116.981 Y112.517 E.17546
G1 X116.848 Y112.384
G1 X116.314 Y112.384
G1 X116.448 Y112.517
G1 X120.613 Y116.683 E.17546
G1 X120.747 Y116.816
G1 X120.214 Y116.816
G1 X120.08 Y116.683
G1 X115.915 Y112.517 E.17546
G1 X115.781 Y112.384
G1 X115.248 Y112.384
G1 X115.381 Y112.517
G1 X119.547 Y116.683 E.17546
G1 X119.68 Y116.816
G1 X119.147 Y116.816
G1 X119.013 Y116.683
G1 X114.848 Y112.517 E.17546
G1 X114.715 Y112.384
G1 X114.181 Y112.384
G1 X114.315 Y112.517
G1 X118.48 Y116.683 E.17546
G1 X118.614 Y116.816
G1 X118.081 Y116.816
G1 X117.947 Y116.683
G1 X113.782 Y112.517 E.17546
G1 X113.648 Y112.384
G1 X113.115 Y112.384
G1 X113.248 Y112.517
G1 X117.414 Y116.683 E.17546
G1 X117.547 Y116.816
G1 X117.014 Y116.816
G1 X116.88 Y116.683
G1 X112.715 Y112.517 E.17546
G1 X112.582 Y112.384
G1 X112.048 Y112.384
G1 X112.182 Y112.517
G1 X116.347 Y116.683 E.17546
G1 X116.481 Y116.816
G1 X115.948 Y116.816
G1 X115.814 Y116.683
G1 X111.649 Y112.517 E.17546
G1 X111.515 Y112.384
G1 X111.284 Y112.686
G1 X111.417 Y112.819
G1 X115.281 Y116.683 E.16274
G1 X115.414 Y116.816
G1 X114.881 Y116.816
G1 X114.747 Y116.683
G1 X111.417 Y113.353 E.14028
G1 X111.284 Y113.219
G1 X111.284 Y113.752
G1 X111.417 Y113.886
G1 X114.214 Y116.683 E.11781
G1 X114.348 Y116.816
G1 X113.814 Y116.816
G1 X113.681 Y116.683
G1 X111.417 Y114.419 E.09535
G1 X111.284 Y114.285
G1 X111.284 Y114.819
G1 X111.417 Y114.952
G1 X113.148 Y116.683 E.07289
G1 X113.281 Y116.816
G1 X112.748 Y116.816
G1 X112.614 Y116.683
G1 X111.417 Y115.486 E.05042
G1 X111.284 Y115.352
G1 X111.284 Y115.885
G1 X111.417 Y116.019
G1 X112.081 Y116.683 E.02796
; close powerlost recovery
M1003 S0
; WIPE_START
G1 F12000
M204 S8000
G1 X111.417 Y116.019 E-.35669
G1 X111.374 Y115.976 E-.02331
; WIPE_END
G1 E-.02 F1800
M204 S10000
G17
G3 Z5.8 I1.217 J0 P1  F60000
; stop printing object, unique label id: 8
M625
M106 S0
M106 P2 S0
M981 S0 P20000 ; close spaghetti detector
; FEATURE: Custom
; MACHINE_END_GCODE_START
; filament end gcode 
;===== date: 20230428 =====================
M400 ; wait for buffer to clear
G92 E0 ; zero the extruder
G1 E-0.8 F1800 ; retract
G1 Z5.9 F900 ; lower z a little
G1 X65 Y245 F12000 ; move to safe pos 
G1 Y265 F3000

G1 X65 Y245 F12000
G1 Y265 F3000
M140 S0 ; turn off bed
M106 S0 ; turn off fan
M106 P2 S0 ; turn off remote part cooling fan
M106 P3 S0 ; turn off chamber cooling fan

G1 X100 F12000 ; wipe
; pull back filament to AMS
M620 S255
G1 X20 Y50 F12000
G1 Y-3
T255
G1 X65 F12000
G1 Y265
G1 X100 F12000 ; wipe
M621 S255
M104 S0 ; turn off hotend

M622.1 S1 ; for prev firmware, default turned on
M1002 judge_flag timelapse_record_flag
M622 J1
    M400 ; wait all motion done
    M991 S0 P-1 ;end smooth timelapse at safe pos
    M400 S3 ;wait for last picture to be taken
M623; end of "timelapse_record_flag"

M400 ; wait all motion done
M17 S
M17 Z0.4 ; lower z motor current to reduce impact if there is something in the bottom

    G1 Z105.4 F600
    G1 Z103.4

M400 P100
M17 R ; restore z current

G90
G1 X128 Y250 F3600

M220 S100  ; Reset feedrate magnitude
M201.2 K1.0 ; Reset acc magnitude
M73.2   R1.0 ;Reset left time magnitude
M1002 set_gcode_claim_speed_level : 0

M17 X0.8 Y0.8 Z0.5 ; lower motor current to 45% power
M73 P100 R0
; EXECUTABLE_BLOCK_END

