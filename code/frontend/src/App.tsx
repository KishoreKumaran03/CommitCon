import { useCallback, useEffect, useState } from "react";
import {
  Activity, AlertTriangle, BarChart3, BookOpen, Building2,
  Check, CheckCircle2, ChevronDown, CircleHelp, Clock3, DoorOpen, Download, GraduationCap,
  LayoutDashboard, LoaderCircle, MapPin, Pencil, Plus, RefreshCw, Search, Settings, ShieldCheck,
  Sparkles, Trash2, Zap,
} from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api, type Allocation, type AllocationOutcome, type Course, type DashboardData, type Room, type RoomOutage } from "./api";

type Page = "Dashboard" | "Classrooms" | "Classes" | "Smart Allocation" | "Availability" | "Settings";
const nav: Array<{ title: Page; icon: typeof LayoutDashboard }> = [
  { title: "Dashboard", icon: LayoutDashboard }, { title: "Classrooms", icon: DoorOpen },
  { title: "Classes", icon: BookOpen }, { title: "Smart Allocation", icon: Sparkles },
  { title: "Availability", icon: Clock3 }, { title: "Settings", icon: Settings },
];
const metricColors: Record<string, string> = {
  blue: "bg-blue-50 text-blue-600",
  violet: "bg-violet-50 text-violet-600",
  green: "bg-green-50 text-green-600",
  amber: "bg-amber-50 text-amber-600",
};
const todayString = () => new Date().toISOString().slice(0, 10);

function App() {
  const [page, setPage] = useState<Page>("Dashboard");
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [classes, setClasses] = useState<Course[]>([]);
  const [allocations, setAllocations] = useState<Allocation[]>([]);
  const [allocationOutcomes, setAllocationOutcomes] = useState<AllocationOutcome[]>([]);
  const [outages, setOutages] = useState<RoomOutage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    setError("");
    try {
      const [d, r, c, a, u] = await Promise.all([
        api<DashboardData>("/dashboard"), api<Room[]>("/classrooms"),
        api<Course[]>("/classes"), api<Allocation[]>("/allocations"), api<RoomOutage[]>("/unavailability"),
      ]);
      setDashboard(d); setRooms(r); setClasses(c); setAllocations(a); setOutages(u);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load CampusFlow data."); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  const runAllocation = async () => {
    if (allocations.length && !window.confirm("This will replace the confirmed allocations. Continue?")) return;
    setBusy(true); setNotice(""); setError("");
    try {
      const result = await api<{ metrics: { successful_allocations: number; unallocated_classes: number }; results: AllocationOutcome[] }>("/allocations/run", {
        method: "POST", body: JSON.stringify({ algorithm: "optimized", replace_existing: allocations.length > 0 }),
      });
      setNotice(`Allocation complete: ${result.metrics.successful_allocations} scheduled classes assigned; ${result.metrics.unallocated_classes} need attention.`);
      await refresh();
      setAllocationOutcomes(result.results);
    } catch (e) { setError(e instanceof Error ? e.message : "Allocation failed."); }
    finally { setBusy(false); }
  };

  return (
    <div className="app-shell flex">
      <aside className="sidebar flex min-h-screen flex-col px-3 py-5">
        <div className="mb-9 flex items-center gap-3 px-2">
          <div className="brand-mark flex h-9 w-9 items-center justify-center rounded-xl"><Activity size={19} /></div>
          <div className="brand-text"><div className="text-[15px] font-bold tracking-wide text-white">CampusFlow</div><div className="mt-0.5 text-[10px] tracking-[.12em] text-slate-400">SMART CAMPUS OPS</div></div>
        </div>
        <div className="sidebar-section-label mb-2 px-3 text-[10px] font-bold uppercase tracking-[.13em] text-slate-500">Workspace</div>
        <nav className="space-y-1">
          {nav.map(({ title, icon: Icon }) => <button key={title} className={`nav-link w-full ${page === title ? "active" : ""}`} onClick={() => setPage(title)} title={title}>
            <Icon size={17} /><span className="nav-label">{title}</span>{title === "Smart Allocation" && <span className="nav-label ml-auto rounded-full bg-blue-400/20 px-1.5 py-0.5 text-[9px] text-blue-200">AI</span>}
          </button>)}
        </nav>
        <div className="mt-auto rounded-xl border border-white/10 bg-white/[.04] p-3.5">
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-slate-200"><ShieldCheck size={15} className="text-emerald-400" />System status</div>
          <div className="flex items-center gap-2 text-[11px] text-slate-400"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> All services operational</div>
          <div className="sidebar-foot-text mt-3 border-t border-white/10 pt-2 text-[10px] text-slate-500">Campus administration · Demo</div>
        </div>
      </aside>
      <main className="min-w-0 flex-1">
        <header className="flex h-[68px] items-center justify-between border-b border-slate-200/80 bg-white px-5 sm:px-8">
          <div className="flex items-center gap-2 text-xs text-slate-400">Campus operations <span>/</span><span className="font-semibold text-slate-700">{page}</span></div>
          <div className="flex items-center gap-3">
            <span className="hidden rounded-md bg-slate-100 px-2.5 py-1.5 text-[11px] font-medium text-slate-600 sm:inline-flex"><MapPin size={13} className="mr-1.5" />Northbridge University</span>
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-50 text-xs font-bold text-blue-700">AD</div>
            <div className="hidden text-xs sm:block"><div className="font-semibold">Administrator</div><div className="text-slate-400">Campus manager</div></div>
            <ChevronDown size={14} className="hidden text-slate-400 sm:block" />
          </div>
        </header>
        <div className="mx-auto max-w-[1500px] p-4 sm:p-7">
          {error && <div className="mb-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"><AlertTriangle size={17} className="mt-0.5 shrink-0" />{error}<button className="ml-auto text-xs font-bold" onClick={() => setError("")}>Dismiss</button></div>}
          {notice && <div className="mb-4 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800"><CheckCircle2 size={17} />{notice}<button className="ml-auto text-xs font-bold" onClick={() => setNotice("")}>Dismiss</button></div>}
          {page === "Dashboard" && <Dashboard data={dashboard} busy={!dashboard} run={runAllocation} refresh={refresh} />}
          {page === "Classrooms" && <Classrooms rooms={rooms} refresh={refresh} notify={setNotice} fail={setError} />}
          {page === "Classes" && <Classes classes={classes} refresh={refresh} notify={setNotice} fail={setError} />}
          {page === "Smart Allocation" && <SmartAllocation allocations={allocations} outcomes={allocationOutcomes} rooms={rooms} refresh={refresh} run={runAllocation} busy={busy} notify={setNotice} fail={setError} />}
          {page === "Availability" && <Availability allocations={allocations} rooms={rooms} outages={outages} />}
          {page === "Settings" && <SettingsPage notify={setNotice} fail={setError} refresh={refresh} />}
        </div>
      </main>
    </div>
  );
}

function PageHeading({ eyebrow, title, text, action }: { eyebrow: string; title: string; text: string; action?: React.ReactNode }) {
  return <div className="mb-6 flex flex-wrap items-end justify-between gap-3"><div><div className="mb-1 text-[10px] font-bold uppercase tracking-[.14em] text-blue-600">{eyebrow}</div><h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1><p className="mt-1 text-sm text-slate-500">{text}</p></div>{action}</div>;
}

function Dashboard({ data, busy, run, refresh }: { data: DashboardData | null; busy: boolean; run: () => void; refresh: () => void }) {
  const metrics = [
    { label: "Classrooms", value: data?.total_classrooms ?? "—", sub: `${data?.active_classrooms ?? 0} active rooms`, icon: Building2, color: "blue" },
    { label: "Available now", value: data?.available_classrooms ?? "—", sub: "Not in an active session", icon: DoorOpen, color: "green" },
    { label: "Scheduled classes", value: data?.total_scheduled ?? "—", sub: `${data?.total_classes ?? 0} courses in catalog`, icon: GraduationCap, color: "violet" },
    { label: "Successful allocations", value: data?.successful_allocations ?? "—", sub: `${data?.unallocated_classes ?? 0} require attention`, icon: CheckCircle2, color: "green" },
    { label: "Seat utilization", value: `${data?.average_seat_utilization ?? 0}%`, sub: "Across valid allocated sessions", icon: BarChart3, color: "amber" },
    { label: "Potential energy difference", value: data?.potential_energy_savings_kwh == null ? "—" : `${data.potential_energy_savings_kwh} kWh`, sub: `vs first-fit · ${data?.energy_comparison_sessions ?? 0} shared sessions`, icon: Zap, color: "green" },
  ];
  return <>
    <PageHeading eyebrow="Campus overview" title="Good morning, Administrator" text="Here’s the current picture of your classroom operations." action={<div className="flex gap-2"><button className="secondary-btn" onClick={refresh}><RefreshCw size={14} />Refresh</button><button className="primary-btn" onClick={run} disabled={busy}><Sparkles size={15} />Run smart allocation</button></div>} />
    <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">{metrics.map(({ label, value, sub, icon: Icon, color }) => <div className="surface p-4" key={label}><div className="flex items-start justify-between"><span className="text-xs font-medium text-slate-500">{label}</span><span className={`flex h-8 w-8 items-center justify-center rounded-lg ${metricColors[color]}`}><Icon size={16} /></span></div><div className="mt-3 text-2xl font-bold text-slate-900">{value}</div><div className="mt-1 text-[11px] text-slate-400">{sub}</div></div>)}</div>
    <div className="mb-5 grid gap-4 xl:grid-cols-[1.6fr_1fr]">
      <section className="surface p-5"><div className="mb-4 flex items-center justify-between"><div><h2 className="text-sm font-bold">Room seat utilization</h2><p className="mt-1 text-xs text-slate-400">Average occupied seats by classroom</p></div><button className="secondary-btn !px-2.5 !py-1.5"><Download size={13} />Export</button></div>
        <div className="h-[240px]">{busy ? <Skeleton /> : <ResponsiveContainer width="100%" height="100%"><BarChart data={data?.room_utilization ?? []} margin={{ top: 5, right: 8, left: -20, bottom: 25 }}><CartesianGrid stroke="#edf1f6" vertical={false} /><XAxis dataKey="name" angle={-35} textAnchor="end" interval={0} tick={{ fontSize: 9, fill: "#8692a6" }} /><YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#8692a6" }} /><Tooltip formatter={(value) => [`${value}%`, "Seat utilization"]} /><Bar dataKey="utilization" fill="#3970e5" radius={[4, 4, 0, 0]} maxBarSize={28} /></BarChart></ResponsiveContainer>}</div>
      </section>
      <section className="surface p-5"><div className="mb-1"><h2 className="text-sm font-bold">Allocation status</h2><p className="mt-1 text-xs text-slate-400">Scheduled sessions in the current dataset</p></div><div className="h-[205px]">{busy ? <Skeleton /> : <ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data?.allocation_status ?? []} dataKey="value" nameKey="name" innerRadius={57} outerRadius={79} paddingAngle={4}>{(data?.allocation_status ?? []).map((_, i) => <Cell key={i} fill={i === 0 ? "#3db585" : "#f2b94b"} />)}</Pie><Tooltip /><text x="50%" y="46%" textAnchor="middle" className="fill-slate-800 text-2xl font-bold">{data?.successful_allocations ?? 0}</text><text x="50%" y="58%" textAnchor="middle" className="fill-slate-400 text-[10px]">allocated</text></PieChart></ResponsiveContainer>}</div><div className="flex justify-center gap-5 text-[11px] text-slate-500"><span><i className="mr-1.5 inline-block h-2 w-2 rounded-full bg-emerald-500" />Allocated</span><span><i className="mr-1.5 inline-block h-2 w-2 rounded-full bg-amber-400" />Unallocated</span></div></section>
    </div>
    <div className="grid gap-4 xl:grid-cols-[1.45fr_1fr]">
      <section className="surface overflow-hidden"><div className="flex items-center justify-between border-b border-slate-100 p-5"><div><h2 className="text-sm font-bold">Upcoming schedule</h2><p className="mt-1 text-xs text-slate-400">Next allocated sessions</p></div><span className="status-pill status-blue">{data?.upcoming_classes.length ?? 0} upcoming</span></div><div className="overflow-x-auto"><table className="w-full text-left"><thead><tr className="table-head"><th className="px-5 py-3">Class</th><th className="px-4 py-3">Date & time</th><th className="px-4 py-3">Room</th><th className="px-5 py-3">Department</th></tr></thead><tbody>{data?.upcoming_classes.slice(0, 5).map((item, i) => <tr key={`${item.class_name}-${i}`} className="border-t border-slate-50 text-xs"><td className="px-5 py-3.5 font-semibold text-slate-700">{item.class_name}</td><td className="px-4 py-3.5 text-slate-500">{item.date}<span className="ml-2 text-slate-400">{item.start_time.slice(0, 5)}</span></td><td className="px-4 py-3.5 font-medium text-blue-700">{item.room}</td><td className="px-5 py-3.5 text-slate-500">{item.department}</td></tr>)}{!data?.upcoming_classes.length && <tr><td colSpan={4} className="p-8 text-center text-sm text-slate-400">No upcoming allocations. Run smart allocation to schedule classes.</td></tr>}</tbody></table></div></section>
      <section className="space-y-4"><div className="surface p-4"><div className="flex items-center gap-3"><div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-50 text-amber-600"><AlertTriangle size={17} /></div><div><h3 className="text-xs font-bold">Conflicts & warnings</h3><p className="text-[11px] text-slate-400">{data?.conflicts_detected ?? 0} constraint issues detected</p></div></div>{data?.conflicts.length ? <div className="mt-3 space-y-2">{data.conflicts.slice(0, 3).map((item, i) => <p key={i} className="rounded-md bg-amber-50 px-2.5 py-2 text-[11px] text-amber-800">{item.message}</p>)}</div> : <p className="mt-3 text-xs text-slate-500">No allocation conflicts found.</p>}</div><div className="surface p-4"><h3 className="text-xs font-bold">Recent allocation activity</h3>{data?.recent_activity.length ? <div className="mt-3 space-y-2.5">{data.recent_activity.slice(0, 4).map((item, i) => <div key={`${item.class_name}-${i}`} className="flex items-center gap-2.5"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-blue-50 text-blue-600"><CheckCircle2 size={14} /></span><div className="min-w-0 flex-1"><div className="truncate text-[11px] font-semibold text-slate-700">{item.class_name}</div><div className="text-[10px] text-slate-400">{item.room} · {item.date}</div></div><span className="text-[9px] text-slate-400">{item.algorithm}</span></div>)}</div> : <p className="mt-3 text-xs text-slate-500">No allocation activity yet.</p>}</div><div className="surface flex items-center justify-between p-4"><div><div className="flex items-center gap-2 text-xs font-bold"><Zap size={15} className="text-emerald-600" />Energy estimate</div><p className="mt-1 text-[11px] text-slate-400">Based on scheduled room power rating</p></div><div className="text-right"><strong className="text-lg">{data?.estimated_energy_kwh ?? 0}</strong><div className="text-[10px] text-slate-400">kWh estimated</div></div></div></section>
    </div>
    <div className="mt-4 flex items-start gap-2 rounded-lg border border-blue-100 bg-blue-50/70 p-3 text-[11px] leading-relaxed text-blue-800"><CircleHelp size={14} className="mt-0.5 shrink-0" />Utilization is allocated students divided by assigned room capacity. The energy figure estimates room rated kW × session hours; it is not metered consumption or verified savings.</div>
  </>;
}

type RoomForm = Omit<Room, "id">;
const defaultRoom: RoomForm = { name: "", building: "", department_preference: "", capacity: 40, projector: false, smart_board: false, computers: false, air_conditioning: false, accessibility_support: false, is_active: true, estimated_power_kw: 2.5 };
function Classrooms({ rooms, refresh, notify, fail }: { rooms: Room[]; refresh: () => Promise<void>; notify: (s: string) => void; fail: (s: string) => void }) {
  const [search, setSearch] = useState(""); const [open, setOpen] = useState(false); const [form, setForm] = useState<RoomForm>(defaultRoom); const [editing, setEditing] = useState<Room | null>(null);
  const [buildingFilter, setBuildingFilter] = useState("all"); const [departmentFilter, setDepartmentFilter] = useState("all");
  const [capacityFilter, setCapacityFilter] = useState(""); const [facilityFilter, setFacilityFilter] = useState("");
  const buildings = [...new Set(rooms.map(room => room.building))].sort();
  const departments = [...new Set(rooms.map(room => room.department_preference).filter(Boolean))].sort();
  const visible = rooms.filter(room =>
    `${room.name} ${room.building} ${room.department_preference}`.toLowerCase().includes(search.toLowerCase())
    && (buildingFilter === "all" || room.building === buildingFilter)
    && (departmentFilter === "all" || room.department_preference === departmentFilter)
    && (!capacityFilter || room.capacity >= Number(capacityFilter))
    && (!facilityFilter || room[facilityFilter as keyof Pick<Room, "projector" | "smart_board" | "computers" | "accessibility_support">]),
  );
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); fail("");
    try {
      await api(editing ? `/classrooms/${editing.id}` : "/classrooms", { method: editing ? "PUT" : "POST", body: JSON.stringify(form) });
      setOpen(false); setEditing(null); setForm(defaultRoom); notify(editing ? "Classroom updated." : "Classroom added."); await refresh();
    } catch (e) { fail(e instanceof Error ? e.message : "Could not save classroom."); }
  };
  const remove = async (id: number) => {
    if (!window.confirm("Delete this classroom? Allocated rooms cannot be deleted.")) return;
    try { await api(`/classrooms/${id}`, { method: "DELETE" }); await refresh(); }
    catch (e) { fail(e instanceof Error ? e.message : "Could not delete classroom."); }
  };
  const toggle = async (room: Room) => {
    const body = { ...room, is_active: !room.is_active };
    try { await api(`/classrooms/${room.id}`, { method: "PUT", body: JSON.stringify(body) }); await refresh(); }
    catch (e) { fail(e instanceof Error ? e.message : "Could not update room."); }
  };
  return <>
    <PageHeading eyebrow="Resource inventory" title="Classrooms" text="Manage room capacity, equipment, and availability." action={<button className="primary-btn" onClick={() => { setEditing(null); setForm(defaultRoom); setOpen(true); }}><Plus size={15} />Add classroom</button>} />
    <div className="surface overflow-hidden"><div className="flex flex-wrap items-center gap-2 border-b border-slate-100 p-4"><div className="relative w-full max-w-sm"><Search size={15} className="absolute left-3 top-2.5 text-slate-400" /><input className="input-field w-full pl-9 text-sm" placeholder="Search classrooms, buildings..." value={search} onChange={e => setSearch(e.target.value)} /></div><select className="input-field !py-2 text-xs" value={buildingFilter} onChange={e => setBuildingFilter(e.target.value)}><option value="all">All buildings</option>{buildings.map(building => <option key={building}>{building}</option>)}</select><select className="input-field !py-2 text-xs" value={departmentFilter} onChange={e => setDepartmentFilter(e.target.value)}><option value="all">All departments</option>{departments.map(department => <option key={department}>{department}</option>)}</select><select className="input-field !py-2 text-xs" value={facilityFilter} onChange={e => setFacilityFilter(e.target.value)}><option value="">Any facility</option><option value="projector">Projector</option><option value="smart_board">Smart board</option><option value="computers">Computers</option><option value="accessibility_support">Accessible</option></select><input className="input-field w-28 !py-2 text-xs" aria-label="Minimum capacity" placeholder="Min seats" type="number" min={1} value={capacityFilter} onChange={e => setCapacityFilter(e.target.value)} /><span className="ml-auto text-xs text-slate-500">{visible.length} rooms</span></div><div className="overflow-x-auto"><table className="w-full text-left"><thead><tr className="table-head bg-slate-50/60"><th className="px-5 py-3">Room</th><th className="px-4 py-3">Building</th><th className="px-4 py-3">Capacity</th><th className="px-4 py-3">Facilities</th><th className="px-4 py-3">Power</th><th className="px-4 py-3">Status</th><th className="px-5 py-3 text-right">Action</th></tr></thead><tbody>{visible.map(room => <tr key={room.id} className="border-t border-slate-100 text-xs hover:bg-slate-50/70"><td className="px-5 py-3.5 font-bold text-slate-800">{room.name}<div className="mt-1 text-[10px] font-normal text-slate-400">{room.department_preference || "General"} preference</div></td><td className="px-4 py-3.5 text-slate-600">{room.building}</td><td className="px-4 py-3.5 font-semibold">{room.capacity} seats</td><td className="px-4 py-3.5"><div className="flex max-w-[210px] flex-wrap gap-1">{[room.projector && "Projector", room.smart_board && "Smart board", room.computers && "Computers", room.accessibility_support && "Accessible"].filter(Boolean).map(f => <span className="rounded bg-slate-100 px-1.5 py-1 text-[9px] text-slate-600" key={String(f)}>{f}</span>)}</div></td><td className="px-4 py-3.5 text-slate-500">{room.estimated_power_kw ?? "—"} kW</td><td className="px-4 py-3.5"><button className={`status-pill ${room.is_active ? "status-green" : "status-red"}`} onClick={() => void toggle(room)}><span className="h-1.5 w-1.5 rounded-full bg-current" />{room.is_active ? "Available" : "Unavailable"}</button></td><td className="px-5 py-3.5 text-right"><button onClick={() => { const fields: RoomForm = { name: room.name, building: room.building, department_preference: room.department_preference, capacity: room.capacity, projector: room.projector, smart_board: room.smart_board, computers: room.computers, air_conditioning: room.air_conditioning, accessibility_support: room.accessibility_support, is_active: room.is_active, estimated_power_kw: room.estimated_power_kw }; setEditing(room); setForm(fields); setOpen(true); }} className="rounded p-1.5 text-slate-400 hover:bg-blue-50 hover:text-blue-600" title="Edit classroom"><Pencil size={14} /></button><button onClick={() => void remove(room.id)} className="rounded p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600" title="Delete classroom"><Trash2 size={14} /></button></td></tr>)}</tbody></table>{!visible.length && <div className="p-12 text-center text-sm text-slate-400">No classrooms match your filters.</div>}</div></div>
    {open && <Modal title={editing ? "Edit classroom" : "Add classroom"} close={() => setOpen(false)}><form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">{textField("Room name", form.name, v => setForm({ ...form, name: v }), true)}{textField("Building", form.building, v => setForm({ ...form, building: v }), true)}{textField("Department preference", form.department_preference, v => setForm({ ...form, department_preference: v }))}<label className="grid gap-1 text-xs font-medium text-slate-600">Capacity<input type="number" min={1} required className="input-field" value={form.capacity} onChange={e => setForm({ ...form, capacity: Number(e.target.value) })} /></label>{(["projector", "smart_board", "computers", "air_conditioning", "accessibility_support"] as const).map(key => <label key={key} className="flex items-center gap-2 text-xs capitalize text-slate-600"><input type="checkbox" checked={form[key]} onChange={e => setForm({ ...form, [key]: e.target.checked })} />{key.replaceAll("_", " ")}</label>)}<label className="grid gap-1 text-xs font-medium text-slate-600">Estimated power (kW)<input type="number" min={0} step=".1" className="input-field" value={form.estimated_power_kw ?? ""} onChange={e => setForm({ ...form, estimated_power_kw: Number(e.target.value) })} /></label><div className="col-span-full mt-2 flex justify-end gap-2"><button type="button" className="secondary-btn" onClick={() => setOpen(false)}>Cancel</button><button className="primary-btn">{editing ? "Save changes" : <><Plus size={14} />Save classroom</>}</button></div></form></Modal>}
  </>;
}

const defaultClass = { name: "", department: "Computer Science", student_count: 30, priority: 1, required_projector: true, required_smart_board: false, required_computers: false, required_accessibility: false, preferred_building: "", preferred_department: "" };
function Classes({ classes, refresh, notify, fail }: { classes: Course[]; refresh: () => Promise<void>; notify: (s: string) => void; fail: (s: string) => void }) {
  const [search, setSearch] = useState(""); const [open, setOpen] = useState(false); const [form, setForm] = useState(defaultClass); const [schedule, setSchedule] = useState({ date: todayString(), start_time: "09:00", end_time: "10:30" }); const [editing, setEditing] = useState<Course | null>(null);
  const [departmentFilter, setDepartmentFilter] = useState("all");
  const departments = [...new Set(classes.map(item => item.department))].sort();
  const visible = classes.filter(item =>
    `${item.name} ${item.department}`.toLowerCase().includes(search.toLowerCase())
    && (departmentFilter === "all" || item.department === departmentFilter),
  );
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); fail("");
    try {
      await api(editing ? `/classes/${editing.id}` : "/classes", {
        method: editing ? "PUT" : "POST", body: JSON.stringify({ ...form, ...schedule }),
      });
      setOpen(false); setForm(defaultClass); setEditing(null); notify(editing ? "Class and schedule updated." : "Class and timetable entry created."); await refresh();
    } catch (e) { fail(e instanceof Error ? e.message : "Could not save class and schedule."); }
  };
  const remove = async (id: number) => {
    if (!window.confirm("Delete this class and its schedules?")) return;
    try { await api(`/classes/${id}`, { method: "DELETE" }); await refresh(); } catch (e) { fail(e instanceof Error ? e.message : "Could not delete class."); }
  };
  return <>
    <PageHeading eyebrow="Academic timetable" title="Classes" text="Manage class sizes, equipment requirements, and scheduled sessions." action={<button className="primary-btn" onClick={() => { setEditing(null); setForm(defaultClass); setSchedule({ date: todayString(), start_time: "09:00", end_time: "10:30" }); setOpen(true); }}><Plus size={15} />Add class</button>} />
    <div className="surface overflow-hidden"><div className="flex flex-wrap items-center gap-3 border-b border-slate-100 p-4"><div className="relative w-full max-w-sm"><Search size={15} className="absolute left-3 top-2.5 text-slate-400" /><input className="input-field w-full pl-9 text-sm" placeholder="Search classes or departments..." value={search} onChange={e => setSearch(e.target.value)} /></div><select className="input-field !py-2 text-xs" value={departmentFilter} onChange={e => setDepartmentFilter(e.target.value)}><option value="all">All departments</option>{departments.map(department => <option key={department}>{department}</option>)}</select><span className="ml-auto text-xs text-slate-500">{visible.length} classes</span></div><div className="overflow-x-auto"><table className="w-full text-left"><thead><tr className="table-head bg-slate-50/60"><th className="px-5 py-3">Class</th><th className="px-4 py-3">Department</th><th className="px-4 py-3">Students</th><th className="px-4 py-3">Requirements</th><th className="px-4 py-3">Next schedule</th><th className="px-5 py-3 text-right">Action</th></tr></thead><tbody>{visible.map(course => <tr key={course.id} className="border-t border-slate-100 text-xs"><td className="px-5 py-3.5 font-semibold text-slate-800">{course.name}<div className="mt-1 text-[10px] font-normal text-slate-400">Priority {course.priority}</div></td><td className="px-4 py-3.5 text-slate-600">{course.department}</td><td className="px-4 py-3.5 font-semibold">{course.student_count}</td><td className="px-4 py-3.5 text-slate-500">{[course.required_projector && "Projector", course.required_smart_board && "Smart board", course.required_computers && "Computers", course.required_accessibility && "Accessible"].filter(Boolean).join(", ") || "None"}</td><td className="px-4 py-3.5 text-slate-500">{course.schedules?.map(s => `${s.date} ${s.start_time.slice(0, 5)}`).join(" · ") || "Not scheduled"}</td><td className="px-5 py-3.5 text-right"><button onClick={() => { setEditing(course); setForm({ ...defaultClass, ...course }); const first = course.schedules?.[0]; setSchedule(first ? { date: first.date, start_time: first.start_time.slice(0, 5), end_time: first.end_time.slice(0, 5) } : { date: todayString(), start_time: "09:00", end_time: "10:30" }); setOpen(true); }} className="rounded p-1.5 text-slate-400 hover:bg-blue-50 hover:text-blue-600" title="Edit class"><Pencil size={14} /></button><button onClick={() => void remove(course.id)} className="rounded p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600" title="Delete class"><Trash2 size={14} /></button></td></tr>)}</tbody></table></div>{!visible.length && <div className="p-12 text-center text-sm text-slate-400">No classes match your filters.</div>}</div>
    {open && <Modal title={editing ? "Edit class & schedule" : "Add class & schedule"} close={() => setOpen(false)}><form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">{textField("Class name", form.name, v => setForm({ ...form, name: v }), true)}<label className="grid gap-1 text-xs font-medium text-slate-600">Department<select className="input-field" value={form.department} onChange={e => setForm({ ...form, department: e.target.value })}>{["Computer Science", "Mathematics", "Physics", "Electronics", "Business", "Arts", "Humanities"].map(d => <option key={d}>{d}</option>)}</select></label><label className="grid gap-1 text-xs font-medium text-slate-600">Student count<input className="input-field" type="number" min={1} required value={form.student_count} onChange={e => setForm({ ...form, student_count: Number(e.target.value) })} /></label><label className="grid gap-1 text-xs font-medium text-slate-600">Priority<select className="input-field" value={form.priority} onChange={e => setForm({ ...form, priority: Number(e.target.value) })}>{[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}</option>)}</select></label>{(["required_projector", "required_smart_board", "required_computers", "required_accessibility"] as const).map(k => <label className="flex items-center gap-2 text-xs text-slate-600" key={k}><input type="checkbox" checked={form[k]} onChange={e => setForm({ ...form, [k]: e.target.checked })} />{k.replace("required_", "").replaceAll("_", " ")}</label>)}<label className="grid gap-1 text-xs font-medium text-slate-600">Preferred building<input className="input-field" value={form.preferred_building} onChange={e => setForm({ ...form, preferred_building: e.target.value })} /></label><label className="grid gap-1 text-xs font-medium text-slate-600">Preferred department block<input className="input-field" value={form.preferred_department} onChange={e => setForm({ ...form, preferred_department: e.target.value })} /></label><label className="grid gap-1 text-xs font-medium text-slate-600">Date<input className="input-field" type="date" required value={schedule.date} onChange={e => setSchedule({ ...schedule, date: e.target.value })} /></label><label className="grid gap-1 text-xs font-medium text-slate-600">Start time<input className="input-field" type="time" required value={schedule.start_time} onChange={e => setSchedule({ ...schedule, start_time: e.target.value })} /></label><label className="grid gap-1 text-xs font-medium text-slate-600">End time<input className="input-field" type="time" required value={schedule.end_time} onChange={e => setSchedule({ ...schedule, end_time: e.target.value })} /></label><div className="col-span-full mt-2 flex justify-end gap-2"><button type="button" className="secondary-btn" onClick={() => setOpen(false)}>Cancel</button><button className="primary-btn">{editing ? "Save changes" : <><Plus size={14} />Save class</>}</button></div></form></Modal>}
  </>;
}

function SmartAllocation({ allocations, outcomes, rooms, refresh, run, busy, notify, fail }: { allocations: Allocation[]; outcomes: AllocationOutcome[]; rooms: Room[]; refresh: () => Promise<void>; run: () => void; busy: boolean; notify: (s: string) => void; fail: (s: string) => void }) {
  const [comparison, setComparison] = useState<Array<Record<string, string | number>>>([]);
  const [compareBusy, setCompareBusy] = useState(false);
  const [emergency, setEmergency] = useState<Allocation | null>(null);
  const [proposal, setProposal] = useState<{ roomId: number; date: string; start_time: string; end_time: string; reason: string } | null>(null);
  const [seed, setSeed] = useState(42);
  const [dateFilter, setDateFilter] = useState("all");
  const [timeFilter, setTimeFilter] = useState("all");
  const [departmentFilter, setDepartmentFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const assignedAllocations = allocations.filter((row): row is Allocation & { classroom_id: number; utilization_percentage: number } =>
    row.classroom_id !== null && row.utilization_percentage !== null,
  );
  const rows: AllocationOutcome[] = outcomes.length ? outcomes : allocations.map(row => ({
    schedule_id: row.schedule_id, class_id: row.class_id, class_name: row.class_name,
    department: row.department, date: row.date, start_time: row.start_time, end_time: row.end_time,
    classroom_id: row.classroom_id, classroom_name: row.classroom_name,
    classroom_building: row.building ?? undefined, student_count: row.student_count, capacity: row.capacity ?? undefined,
    unused_seats: row.unused_seats ?? undefined, utilization_percentage: row.utilization_percentage ?? undefined,
    status: row.classroom_id !== null ? "allocated" : "unallocated", explanation: row.explanation, reason: row.reason ?? undefined,
  }));
  const filteredRows = rows.filter(row =>
    (dateFilter === "all" || row.date === dateFilter)
    && (timeFilter === "all" || row.start_time.slice(0, 5) === timeFilter)
    && (departmentFilter === "all" || row.department === departmentFilter)
    && (statusFilter === "all" || row.status === statusFilter),
  );
  const dates = [...new Set(rows.map(row => row.date))].sort();
  const departments = [...new Set(rows.map(row => row.department))].sort();
  const compare = async () => {
    setCompareBusy(true); fail("");
    try {
      const data = await api<{ results: Array<Record<string, string | number>> }>(`/simulations/compare?seed=${seed}`, { method: "POST" });
      setComparison(data.results);
    } catch (e) { fail(e instanceof Error ? e.message : "Comparison failed."); }
    finally { setCompareBusy(false); }
  };
  const startEmergency = (row: Allocation & { classroom_id: number }) => {
    setEmergency(row);
    setProposal({
      roomId: row.classroom_id, date: row.date,
      start_time: row.start_time.slice(0, 5), end_time: row.end_time.slice(0, 5),
      reason: "Emergency closure",
    });
  };
  const suggest = async () => {
    if (!emergency || !proposal) return;
    try {
      const result = await api<{ proposals: Array<{ from_room: string; to_room: string | null; class_name: string; status: string; reason: string }>; affected_count: number }>(`/classrooms/${proposal.roomId}/unavailability`, {
        method: "POST", body: JSON.stringify({ ...proposal, apply: false }),
      });
      if (!result.affected_count) {
        if (!window.confirm("No current allocations overlap this outage. Record the room unavailability anyway?")) return;
        await api(`/classrooms/${proposal.roomId}/unavailability`, { method: "POST", body: JSON.stringify({ ...proposal, apply: true }) });
        notify("Room unavailability recorded; no current allocations required reassignment.");
        setEmergency(null);
        await refresh();
        return;
      }
      const detail = result.proposals.map(p => `${p.class_name}: ${p.from_room} → ${p.to_room ?? "No option"} — ${p.reason}`).join("\n");
      if (!window.confirm(`Emergency reallocation plan:\n\n${detail}\n\nApply these changes?`)) return;
      await api(`/classrooms/${proposal.roomId}/unavailability`, { method: "POST", body: JSON.stringify({ ...proposal, apply: true }) });
      notify("Emergency reassignment applied atomically."); setEmergency(null); await refresh();
    } catch (e) { fail(e instanceof Error ? e.message : "Could not propose reassignment."); }
  };
  return <>
    <PageHeading eyebrow="Constraint-aware optimization" title="Smart allocation" text="Compare allocation strategies, review explainable results, and resolve room emergencies." action={<button className="primary-btn" disabled={busy} onClick={run}>{busy ? <LoaderCircle className="animate-spin" size={15} /> : <Sparkles size={15} />}{busy ? "Optimizing..." : "Run allocation"}</button>} />
    <div className="mb-4 grid gap-3 sm:grid-cols-3"><div className="surface p-4"><div className="text-xs text-slate-500">Allocated sessions</div><div className="mt-2 text-2xl font-bold">{assignedAllocations.length}</div><div className="mt-1 text-[11px] text-slate-400">{Math.max(rows.length - assignedAllocations.length, 0)} unallocated in latest run</div></div><div className="surface p-4"><div className="text-xs text-slate-500">Current average utilization</div><div className="mt-2 text-2xl font-bold">{assignedAllocations.length ? (assignedAllocations.reduce((sum, row) => sum + row.utilization_percentage, 0) / assignedAllocations.length).toFixed(1) : 0}%</div><div className="mt-1 text-[11px] text-slate-400">Mean per scheduled session</div></div><div className="surface flex items-center gap-3 p-4"><div className="rounded-lg bg-emerald-50 p-2.5 text-emerald-600"><ShieldCheck size={19} /></div><div><div className="text-xs font-semibold">Hard constraints enforced</div><div className="mt-1 text-[11px] text-slate-400">Capacity · facilities · availability · conflicts</div></div></div></div>
    <section className="surface mb-4 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-4"><div><h2 className="text-sm font-bold">Allocation results</h2><p className="mt-1 text-xs text-slate-400">Room assignment and seat utilization by scheduled class</p></div><span className="status-pill status-blue">{rows.length} schedule results</span></div>
      <div className="flex flex-wrap gap-2 border-b border-slate-100 p-4">
        <select className="input-field !py-2 text-xs" value={dateFilter} onChange={e => setDateFilter(e.target.value)}><option value="all">All dates</option>{dates.map(date => <option key={date}>{date}</option>)}</select>
        <select className="input-field !py-2 text-xs" value={timeFilter} onChange={e => setTimeFilter(e.target.value)}><option value="all">All time slots</option>{["09:00", "10:30", "13:00", "14:30"].map(slot => <option key={slot}>{slot}</option>)}</select>
        <select className="input-field !py-2 text-xs" value={departmentFilter} onChange={e => setDepartmentFilter(e.target.value)}><option value="all">All departments</option>{departments.map(department => <option key={department}>{department}</option>)}</select>
        <select className="input-field !py-2 text-xs" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}><option value="all">All statuses</option><option value="allocated">Allocated</option><option value="unallocated">Unallocated</option></select>
      </div>
      <div className="scrollbar-thin overflow-x-auto"><table className="w-full text-left"><thead><tr className="table-head bg-slate-50/50"><th className="px-5 py-3">Class / time</th><th className="px-4 py-3">Assigned room</th><th className="px-4 py-3">Seats</th><th className="px-4 py-3">Utilization</th><th className="px-4 py-3">Explanation / reason</th><th className="px-5 py-3">Action</th></tr></thead><tbody>{filteredRows.map(row => {
        const persisted = allocations.find((allocation): allocation is Allocation & { classroom_id: number } =>
          allocation.schedule_id === row.schedule_id && allocation.classroom_id !== null,
        );
        return <tr key={row.schedule_id} className="border-t border-slate-100 text-xs">
          <td className="px-5 py-3.5"><div className="font-semibold">{row.class_name}</div><div className="mt-1 text-[10px] text-slate-400">{row.date} · {row.start_time.slice(0, 5)}–{row.end_time.slice(0, 5)}</div></td>
          <td className="px-4 py-3.5">{row.status === "allocated" ? <><div className="font-semibold text-blue-700">{row.classroom_name}</div><div className="text-[10px] text-slate-400">{row.classroom_building ?? persisted?.building ?? ""}</div></> : <span className="status-pill status-red">Unallocated</span>}</td>
          <td className="px-4 py-3.5 text-slate-600">{row.status === "allocated" ? <>{row.student_count} / {row.capacity}<div className="text-[10px] text-slate-400">{row.unused_seats} unused</div></> : `${row.student_count ?? "—"} students`}</td>
          <td className="px-4 py-3.5">{row.status === "allocated" ? <div className="flex items-center gap-2"><div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-emerald-500" style={{ width: `${row.utilization_percentage ?? 0}%` }} /></div><span>{row.utilization_percentage}%</span></div> : "—"}</td>
          <td className="max-w-[290px] px-4 py-3.5 text-[10px] leading-relaxed text-slate-500">{row.status === "allocated" ? row.explanation : row.reason}</td>
          <td className="px-5 py-3.5">{persisted && <button className="secondary-btn !px-2.5 !py-1.5 !text-[10px]" onClick={() => startEmergency(persisted)}><AlertTriangle size={12} />Emergency</button>}</td>
        </tr>;
      })}</tbody></table>{!filteredRows.length && <Empty message="No results match these filters. Run allocation to generate a current result set." />}</div>
    </section>
    <section className="surface p-5">
      <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-sm font-bold">Algorithm comparison</h2><p className="mt-1 text-xs text-slate-400">Same rooms, schedules, and hard constraints across each strategy.</p></div><div className="flex items-center gap-2"><label className="text-[11px] text-slate-500">Random seed</label><input className="input-field w-20 !py-2 text-xs" type="number" value={seed} onChange={e => setSeed(Number(e.target.value))} /><button className="primary-btn" disabled={compareBusy} onClick={() => void compare}>{compareBusy ? <LoaderCircle size={14} className="animate-spin" /> : <BarChart3 size={14} />}Compare algorithms</button></div></div>
      {comparison.length > 0 && <div className="mt-5 overflow-x-auto"><table className="w-full text-left"><thead><tr className="table-head"><th className="py-3">Method</th><th className="px-3 py-3">Success</th><th className="px-3 py-3">Rate</th><th className="px-3 py-3">Unused seats</th><th className="px-3 py-3">Seat utilization</th><th className="px-3 py-3">Preference penalty</th><th className="px-3 py-3">Runtime</th></tr></thead><tbody>{comparison.map(row => <tr key={String(row.algorithm)} className="border-t border-slate-100 text-xs"><td className="py-3 font-semibold capitalize">{String(row.algorithm).replace("_", " ")}</td><td className="px-3 py-3">{row.successful_allocations}</td><td className="px-3 py-3">{row.success_rate}%</td><td className="px-3 py-3">{row.unused_seats}</td><td className="px-3 py-3">{row.utilization_percentage}%</td><td className="px-3 py-3">{row.preference_penalty}</td><td className="px-3 py-3">{row.runtime_ms} ms</td></tr>)}</tbody></table><div className="mt-4 h-[220px]"><ResponsiveContainer width="100%" height="100%"><BarChart data={comparison} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}><CartesianGrid stroke="#edf1f6" vertical={false} /><XAxis dataKey="algorithm" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 10 }} /><Tooltip /><Bar dataKey="successful_allocations" name="Allocated" fill="#3970e5" radius={[5, 5, 0, 0]} /><Bar dataKey="unallocated_classes" name="Unallocated" fill="#f1ae43" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer></div><p className="mt-2 text-[10px] text-slate-400">Metrics are calculated from the live scenario. This optimizer uses a deterministic heuristic, not a globally optimality-guaranteed solver.</p></div>}
    </section>
    {emergency && proposal && <Modal title="Emergency room reassignment" close={() => setEmergency(null)}><div className="mb-4 rounded-lg bg-amber-50 p-3 text-xs leading-relaxed text-amber-900">Mark <strong>{rooms.find(r => r.id === proposal.roomId)?.name}</strong> unavailable. The system will identify impacted allocations and propose valid alternatives. Changes require your confirmation.</div><div className="grid gap-3 sm:grid-cols-2"><label className="grid gap-1 text-xs font-medium">Date<input className="input-field" type="date" value={proposal.date} onChange={e => setProposal({ ...proposal, date: e.target.value })} /></label><label className="grid gap-1 text-xs font-medium">Reason<input className="input-field" value={proposal.reason} onChange={e => setProposal({ ...proposal, reason: e.target.value })} /></label><label className="grid gap-1 text-xs font-medium">Unavailable from<input className="input-field" type="time" value={proposal.start_time} onChange={e => setProposal({ ...proposal, start_time: e.target.value })} /></label><label className="grid gap-1 text-xs font-medium">Unavailable until<input className="input-field" type="time" value={proposal.end_time} onChange={e => setProposal({ ...proposal, end_time: e.target.value })} /></label></div><div className="mt-5 flex justify-end gap-2"><button className="secondary-btn" onClick={() => setEmergency(null)}>Cancel</button><button className="primary-btn" onClick={() => void suggest()}><Check size={14} />Review & apply proposal</button></div></Modal>}
  </>;
}

function Availability({ allocations, rooms, outages }: { allocations: Allocation[]; rooms: Room[]; outages: RoomOutage[] }) {
  const [day, setDay] = useState(allocations[0]?.date ?? outages[0]?.date ?? todayString());
  const dayRows = allocations.filter(row => row.date === day);
  const slots = ["09:00", "10:30", "12:00", "13:00", "14:30", "16:00"];
  return <>
    <PageHeading eyebrow="Timetable view" title="Room availability" text="Inspect room occupancy by day and identify scheduled sessions." action={<label className="flex items-center gap-2 text-xs text-slate-500">Schedule date<input className="input-field !py-2" type="date" value={day} onChange={e => setDay(e.target.value)} /></label>} />
    <div className="mb-4 flex flex-wrap gap-2 text-[11px]"><span className="status-pill status-green">Allocated session</span><span className="status-pill status-red">Unavailable room</span><span className="status-pill status-blue">Active room</span></div>
    <div className="surface overflow-x-auto"><table className="w-full min-w-[800px] text-left"><thead><tr><th className="table-head sticky left-0 bg-slate-50 px-4 py-3">Classroom</th>{slots.slice(0, -1).map((slot, i) => <th key={slot} className="table-head min-w-[145px] border-l border-slate-100 px-3 py-3">{slot} – {slots[i + 1]}</th>)}</tr></thead><tbody>{rooms.map(room => <tr key={room.id} className="border-t border-slate-100"><td className="sticky left-0 bg-white px-4 py-3"><div className="text-xs font-bold">{room.name}</div><div className="text-[10px] text-slate-400">{room.capacity} seats · {room.building}</div></td>{slots.slice(0, -1).map((slot, i) => { const end = slots[i + 1]; const match = dayRows.find(row => row.classroom_id === room.id && row.start_time.slice(0, 5) < end && row.end_time.slice(0, 5) > slot); const outage = outages.find(row => row.classroom_id === room.id && row.date === day && row.start_time.slice(0, 5) < end && row.end_time.slice(0, 5) > slot); return <td className="border-l border-slate-100 px-2 py-2" key={`${room.id}-${slot}`}>{match ? <div className="rounded-md border border-emerald-100 bg-emerald-50 px-2 py-2"><div className="truncate text-[10px] font-bold text-emerald-800">{match.class_name}</div><div className="mt-1 text-[9px] text-emerald-700">{match.start_time.slice(0, 5)}–{match.end_time.slice(0, 5)}</div></div> : outage || !room.is_active ? <div className="rounded-md bg-red-50 px-2 py-2 text-[10px] text-red-600">{outage?.reason ?? "Unavailable"}</div> : <div className="rounded-md bg-slate-50 px-2 py-2 text-[10px] text-slate-300">Available</div>}</td>; })}</tr>)}</tbody></table>{!rooms.length && <Empty message="No classrooms have been configured." />}</div>
  </>;
}

function SettingsPage({ notify, fail, refresh }: { notify: (s: string) => void; fail: (s: string) => void; refresh: () => Promise<void> }) {
  const [settings, setSettings] = useState({ seat_weight: 1, department_weight: 30, building_weight: 15, disruption_weight: 50, energy_weight: 0 });
  useEffect(() => { api<typeof settings>("/settings").then(setSettings).catch(e => fail(e instanceof Error ? e.message : "Could not load settings.")); }, [fail]);
  const fields: Array<[keyof typeof settings, string, string]> = [
    ["seat_weight", "Seat capacity efficiency", "Penalty per unused seat."],
    ["department_weight", "Department preference", "Penalty for department-block mismatch."],
    ["building_weight", "Preferred building", "Penalty for building mismatch."],
    ["disruption_weight", "Reallocation disruption", "Configured for emergency-planning extensions."],
    ["energy_weight", "Estimated energy", "Penalty per estimated kWh (zero by default)."],
  ];
  const save = async () => {
    try { await api("/settings", { method: "PUT", body: JSON.stringify(settings) }); notify("Optimization weights saved."); }
    catch (e) { fail(e instanceof Error ? e.message : "Could not save settings."); }
  };
  const resetDemo = async () => {
    if (!window.confirm("Reset all demo rooms, classes, allocations, and simulation history? This cannot be undone.")) return;
    try {
      const result = await api<{ message: string; classrooms: number; classes: number }>("/demo/reset", { method: "POST" });
      notify(`${result.message} ${result.classrooms} rooms and ${result.classes} classes loaded.`);
      setSettings({ seat_weight: 1, department_weight: 30, building_weight: 15, disruption_weight: 50, energy_weight: 0 });
      await refresh();
    } catch (e) { fail(e instanceof Error ? e.message : "Could not reset demonstration data."); }
  };
  return <><PageHeading eyebrow="Optimization preferences" title="Settings" text="Tune the soft-constraint objective. Mandatory room requirements remain fixed." /><div className="surface max-w-3xl p-5 sm:p-7"><div className="mb-5 border-b border-slate-100 pb-4"><h2 className="text-sm font-bold">Allocation weights</h2><p className="mt-1 text-xs text-slate-400">Higher values increase the optimizer’s penalty for the corresponding soft-constraint tradeoff.</p></div><div className="space-y-4">{fields.map(([key, label, help]) => <label key={key} className="grid gap-2 sm:grid-cols-[1fr_140px] sm:items-center"><span><span className="block text-xs font-semibold text-slate-700">{label}</span><span className="mt-1 block text-[11px] text-slate-400">{help}</span></span><input className="input-field" type="number" min={0} step=".5" value={settings[key]} onChange={e => setSettings({ ...settings, [key]: Number(e.target.value) })} /></label>)}</div><div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-4"><span className="text-[11px] text-slate-400">Hard constraints cannot be disabled.</span><button className="primary-btn" onClick={() => void save()}>Save settings</button></div></div><div className="surface mt-5 flex max-w-3xl flex-wrap items-center justify-between gap-4 border-red-100 p-5"><div><h2 className="text-sm font-bold text-slate-800">Demonstration data</h2><p className="mt-1 max-w-xl text-xs leading-relaxed text-slate-500">Reload the sample classrooms and timetable. This also clears allocations and benchmark history.</p></div><button className="secondary-btn !border-red-200 !text-red-700 hover:!bg-red-50" onClick={() => void resetDemo()}><RefreshCw size={14} />Reset demo data</button></div></>;
}

function Modal({ title, close, children }: { title: string; close: () => void; children: React.ReactNode }) {
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4" onMouseDown={e => { if (e.target === e.currentTarget) close(); }}><div className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-5 shadow-xl sm:p-6"><div className="mb-5 flex items-center justify-between"><h2 className="text-base font-bold">{title}</h2><button className="text-slate-400 hover:text-slate-700" onClick={close}>✕</button></div>{children}</div></div>;
}
function textField(label: string, value: string, change: (value: string) => void, required = false) {
  return <label className="grid gap-1 text-xs font-medium text-slate-600">{label}<input className="input-field" required={required} value={value} onChange={e => change(e.target.value)} /></label>;
}
function Empty({ message }: { message: string }) { return <div className="p-12 text-center text-sm text-slate-400">{message}</div>; }
function Skeleton() { return <div className="h-full animate-pulse rounded-lg bg-slate-50" />; }

export default App;
