import { FormEvent, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera, ImagePlus, Save, Scan, Trash2, UserRound } from "lucide-react";
import { Link, Navigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { captureFaceSamples } from "../face/descriptor";

const SUGGESTED = ["paracetamol", "ibuprofen", "AINS", "smecta", "amoxicillin", "azithromycin"];

function compressImage(source: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => {
      const canvas = document.createElement("canvas");
      const size = 320;
      canvas.width = size;
      canvas.height = size;
      const context = canvas.getContext("2d");
      if (!context) {
        reject(new Error("Canvas indisponible"));
        return;
      }
      const scale = Math.max(size / image.width, size / image.height);
      const width = image.width * scale;
      const height = image.height * scale;
      context.drawImage(image, (size - width) / 2, (size - height) / 2, width, height);
      resolve(canvas.toDataURL("image/jpeg", 0.72));
    };
    image.onerror = () => reject(new Error("Image illisible"));
    image.src = source;
  });
}

export default function ProfilePage() {
  const { code } = useParams();
  const { user, refreshUser } = useAuth();
  const queryClient = useQueryClient();
  const target = code || user?.crew_member_code || "";
  const canEdit = user?.role === "admin" || user?.crew_member_code === target;
  const isAdmin = user?.role === "admin";

  const profile = useQuery({
    queryKey: ["crew-member", target],
    queryFn: () => api.crewMember(target),
    enabled: Boolean(target) && canEdit,
  });
  const crew = useQuery({
    queryKey: ["crew"],
    queryFn: api.crew,
    enabled: isAdmin,
  });

  const [allergies, setAllergies] = useState<string[]>([]);
  const [draft, setDraft] = useState("");
  const [avatar, setAvatar] = useState<string | null>(null);
  const [cameraOn, setCameraOn] = useState(false);
  const [faceCameraOn, setFaceCameraOn] = useState(false);
  const [error, setError] = useState("");
  const [faceStatus, setFaceStatus] = useState("");
  const videoRef = useRef<HTMLVideoElement>(null);
  const faceVideoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const faceStreamRef = useRef<MediaStream | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!profile.data) return;
    setAllergies(profile.data.allergies || []);
    setAvatar(profile.data.avatar_data || null);
  }, [profile.data]);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      faceStreamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  async function startCamera() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: 640, height: 480 },
        audio: false,
      });
      streamRef.current = stream;
      setCameraOn(true);
      if (videoRef.current) videoRef.current.srcObject = stream;
    } catch {
      setError("Camera inaccessible. Autorisez-la ou importez une photo.");
    }
  }

  function stopCamera() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setCameraOn(false);
  }

  async function startFaceCamera() {
    setError("");
    setFaceStatus("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: 480, height: 480 },
        audio: false,
      });
      faceStreamRef.current = stream;
      setFaceCameraOn(true);
      if (faceVideoRef.current) faceVideoRef.current.srcObject = stream;
    } catch {
      setError("Camera inaccessible pour la reconnaissance faciale.");
    }
  }

  function stopFaceCamera() {
    faceStreamRef.current?.getTracks().forEach((track) => track.stop());
    faceStreamRef.current = null;
    setFaceCameraOn(false);
  }

  async function captureFrame() {
    const video = videoRef.current;
    if (!video) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const context = canvas.getContext("2d");
    if (!context) return;
    context.drawImage(video, 0, 0);
    const compressed = await compressImage(canvas.toDataURL("image/jpeg", 0.85));
    setAvatar(compressed);
    stopCamera();
  }

  async function onFile(file: File) {
    const raw = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = () => reject(new Error("Lecture impossible"));
      reader.readAsDataURL(file);
    });
    setAvatar(await compressImage(raw));
  }

  function addAllergy(value: string) {
    const cleaned = value.trim();
    if (!cleaned || allergies.includes(cleaned)) return;
    setAllergies((current) => [...current, cleaned]);
    setDraft("");
  }

  const save = useMutation({
    mutationFn: () =>
      api.updateProfile(target, {
        allergies,
        avatar_data: avatar,
        full_name: profile.data?.full_name,
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["crew"] }),
        queryClient.invalidateQueries({ queryKey: ["crew-member", target] }),
        refreshUser(),
      ]);
    },
  });

  const enrollFace = useMutation({
    mutationFn: async () => {
      const video = faceVideoRef.current;
      if (!video) throw new Error("Camera faciale indisponible");
      setFaceStatus("Capture de 4 echantillons...");
      const samples = await captureFaceSamples(video, 4, 180);
      return api.enrollFace(target, samples);
    },
    onSuccess: async (result) => {
      stopFaceCamera();
      setFaceStatus(`Reconnaissance faciale enregistree (${result.samples} echantillons).`);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["crew"] }),
        queryClient.invalidateQueries({ queryKey: ["crew-member", target] }),
      ]);
    },
    onError: (caught) => {
      setFaceStatus("");
      setError(caught instanceof Error ? caught.message : "Enregistrement facial impossible");
    },
  });

  const clearFace = useMutation({
    mutationFn: () => api.clearFace(target),
    onSuccess: async () => {
      setFaceStatus("Reconnaissance faciale effacee.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["crew"] }),
        queryClient.invalidateQueries({ queryKey: ["crew-member", target] }),
      ]);
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (draft.trim()) addAllergy(draft);
    save.mutate();
  }

  if (!canEdit) return <Navigate to="/dashboard" replace />;

  return (
    <div className="profile-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Identite / Dossier de bord</span>
          <h1>Profil equipage</h1>
          <p>Photo, camera, allergies et reconnaissance faciale. Medichat s'en sert pour ecarter les molecules dangereuses.</p>
        </div>
      </div>

      <form className="profile-grid" onSubmit={onSubmit}>
        <section className="glass-panel profile-photo">
          <div className="profile-preview">
            {avatar ? <img src={avatar} alt="Photo de profil" /> : <UserRound size={42} />}
          </div>
          {cameraOn && (
            <video ref={videoRef} className="profile-camera" autoPlay playsInline muted />
          )}
          <div className="profile-photo-actions">
            <button type="button" onClick={() => fileRef.current?.click()}>
              <ImagePlus size={16} /> Importer
            </button>
            {cameraOn ? (
              <>
                <button type="button" onClick={captureFrame}>
                  <Camera size={16} /> Capturer
                </button>
                <button type="button" onClick={stopCamera}>Arreter</button>
              </>
            ) : (
              <button type="button" onClick={startCamera}>
                <Camera size={16} /> Se filmer
              </button>
            )}
            {avatar && (
              <button type="button" className="danger-ghost" onClick={() => setAvatar(null)}>
                <Trash2 size={16} /> Retirer
              </button>
            )}
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            hidden
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) onFile(file);
            }}
          />
        </section>

        <section className="glass-panel profile-form">
          <h2>{profile.data?.full_name ?? user?.full_name}</h2>
          <p>{profile.data?.age ?? user?.age ?? "--"} ans / code {target}</p>

          <label htmlFor="allergy-input">Allergies</label>
          <div className="allergy-chips">
            {allergies.map((item) => (
              <button type="button" key={item} onClick={() => setAllergies((current) => current.filter((value) => value !== item))}>
                {item} x
              </button>
            ))}
            {!allergies.length && <span>Aucune allergie enregistree</span>}
          </div>
          <div className="allergy-suggest">
            {SUGGESTED.map((item) => (
              <button type="button" key={item} onClick={() => addAllergy(item)} disabled={allergies.includes(item)}>
                {item}
              </button>
            ))}
          </div>
          <div className="allergy-add">
            <input
              id="allergy-input"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Autre allergene, ex. paracetamol"
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  addAllergy(draft);
                }
              }}
            />
            <button type="button" onClick={() => addAllergy(draft)}>Ajouter</button>
          </div>

          {(error || save.error) && (
            <p className="form-error" role="alert">{error || save.error?.message}</p>
          )}
          {save.isSuccess && <p className="form-ok">Profil sauvegarde. Medichat utilisera ces allergies.</p>}

          <button className="profile-save" type="submit" disabled={save.isPending}>
            <Save size={17} /> {save.isPending ? "Enregistrement..." : "Sauvegarder le profil"}
          </button>
        </section>
      </form>

      {isAdmin && (
        <section className="glass-panel face-enroll">
          <div className="section-heading">
            <h2>Reconnaissance faciale</h2>
            <p>
              Raphael configure les identites de tout l'equipage. Empreinte 32x32 locale,
              jamais de photo dans la table reconnaissance_faciale.
            </p>
          </div>
          <p className="face-target">Cible: {profile.data?.full_name ?? target}</p>
          {faceCameraOn && (
            <video ref={faceVideoRef} className="face-preview" autoPlay playsInline muted />
          )}
          <div className="profile-photo-actions">
            {faceCameraOn ? (
              <>
                <button type="button" onClick={() => enrollFace.mutate()} disabled={enrollFace.isPending}>
                  <Scan size={16} /> {enrollFace.isPending ? "Capture..." : "Enregistrer le visage"}
                </button>
                <button type="button" onClick={stopFaceCamera}>Eteindre</button>
              </>
            ) : (
              <button type="button" onClick={startFaceCamera}>
                <Camera size={16} /> Filmer pour Face ID
              </button>
            )}
            {profile.data?.face_enrolled && (
              <button type="button" className="danger-ghost" onClick={() => clearFace.mutate()} disabled={clearFace.isPending}>
                <Trash2 size={16} /> Effacer Face ID
              </button>
            )}
          </div>
          <p>{profile.data?.face_enrolled ? `${profile.data.face_samples} echantillon(s) enregistres` : "Aucun visage enregistre pour ce profil"}</p>
          {faceStatus && <p className="form-ok">{faceStatus}</p>}

          {crew.data && (
            <div className="crew-face-list">
              {crew.data.map((member) => (
                <Link key={member.code} to={`/profil/${member.code}`} className={member.code === target ? "selected" : ""}>
                  <strong>{member.full_name}</strong>
                  <span>{member.face_enrolled ? "Enrole" : "A configurer"}</span>
                </Link>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
