export const api = async <T,>(path: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
};

export type Room = {
  id: number; name: string; building: string; department_preference: string; capacity: number;
  projector: boolean; smart_board: boolean; computers: boolean; air_conditioning: boolean;
  accessibility_support: boolean; is_active: boolean; estimated_power_kw: number | null;
};
export type Course = {
  id: number; name: string; department: string; student_count: number; priority: number;
  required_projector: boolean; required_smart_board: boolean; required_computers: boolean;
  required_accessibility: boolean; preferred_building: string; preferred_department: string;
  schedules?: Array<{ id: number; date: string; start_time: string; end_time: string; allocation?: Allocation | null }>;
};
export type Allocation = {
  id: number; schedule_id: number; class_id: number; class_name: string; department: string; student_count: number;
  date: string; start_time: string; end_time: string; classroom_id: number | null; classroom_name: string | null;
  building: string | null; capacity: number | null; unused_seats: number | null; utilization_percentage: number | null;
  status: "confirmed" | "unallocated"; algorithm_name: string; explanation: string; reason?: string | null;
};
export type AllocationOutcome = {
  schedule_id: number; class_id: number; class_name: string; department: string;
  date: string; start_time: string; end_time: string; classroom_id: number | null;
  classroom_name: string | null; classroom_building?: string; student_count?: number;
  capacity?: number; unused_seats?: number; utilization_percentage?: number;
  status: "allocated" | "unallocated"; explanation?: string; reason?: string;
};
export type RoomOutage = {
  id: number; classroom_id: number; classroom_name: string; date: string;
  start_time: string; end_time: string; reason: string;
};
export type DashboardData = {
  total_classrooms: number; active_classrooms: number; available_classrooms: number; total_classes: number;
  total_scheduled: number; successful_allocations: number; unallocated_classes: number;
  conflicts_detected: number; average_seat_utilization: number; estimated_energy_kwh: number;
  potential_energy_savings_kwh: number | null; energy_comparison_sessions: number;
  room_utilization: Array<{ name: string; utilization: number; sessions: number }>;
  allocation_status: Array<{ name: string; value: number }>;
  recent_activity: Array<{ class_name: string; room: string; date: string; algorithm: string }>;
  upcoming_classes: Array<{ class_name: string; department: string; room: string; date: string; start_time: string; end_time: string }>;
  conflicts: Array<{ message: string }>;
};
