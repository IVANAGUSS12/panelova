from datetime import datetime, timedelta
from io import BytesIO

import openpyxl
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from django.utils import timezone
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils.dateparse import parse_date

from .forms import QRPatientForm, AttachmentForm, PatientFilterForm, ReprogramForm
from .models import Patient, Attachment

SERVICIOS_QR = [
    'TRAUMATOLOGIA',
    'HEMODINAMIA',
]

MEDICOS_QR = [
    'ABALO EDUARDO', 'ADROGUE LUIS', 'BARBIERI PABLO', 'CARRIZO JUAN',
    'CHAVEZ ARIEL', 'CONSTANZA EDUARDO', 'CORDOBA ALEJANDRA',
    'DE ZAVALIA MAXIMO', 'DEIMUNDO MARCOS', 'DEVOTO MATIAS',
    'GOBBI ENRIQUE', 'GRANDOLI FERNANDO', 'IGLESIAS ALEJANDRO',
    'MALLEA ANDRES', 'MENINATO MARCOS', 'MOUNIER CARLOS',
    'ORTIZ EZEQUIEL', 'PEREA AGUSTIN', 'PINOTTI NORBERTO',
    'SANNA HERNAN', 'SERE IGNACIO', 'TORGA SPAK ROGER',
    'VALENTINI ROBERTO', 'VILLA NATALIA', 'YAVEN IGNACIO',
    'YEREGUI SANTIAGO',
]

COBERTURAS_QR = [
    'ACADEMIA NACIONAL DE MEDICINA',
    'ACMED',
    'ACMED',
    'AMEPBA',
    'AMEPBA',
    'ANDAR',
    'APM',
    'APRES',
    'APSOT',
    'SANCOR',
    'ASOCIACION MUTUAL RURALISTA',
    'AVALIAN',
    'AVALIAN',
    'C.S.I.L',
    'CAJA NOTARIAL',
    'CEMIC',
    'CINME',
    'CIRC.MED.LOMAS ZAMORA',
    'CIRCULO MEDICO DE LA MATANZA',
    'COBENSIL',
    'COLEGIO ESCRIBANOS PROVINCIA',
    'CONEXA',
    'CONF. EPISCOPAL ARG.',
    'CONVENIO OBRA SOCIAL',
    'CORPORACION ASISTENCIAL',
    'DASMI',
    'DASMI',
    'ELEVAR',
    'ENSALUD',
    'FAMYL',
    'GALENO',
    'GENESEN',
    'HOPE',
    'HOSPITAL BRITANICO',
    'INST.O.S EMPLEADO PROVINCIAL',
    'JERARQUICOS SALUD',
    'LUIS PASTEUR',
    'MEDICALS',
    'MEDICUS',
    'MEDIFE',
    'MEDIN',
    'MEDIPREMIUM',
    'MEDITAR',
    'MITA',
    'MUTUAL FEDERADA 25 DE JUNIO',
    'MUTUAL MEDICA CONCORDIA',
    'NEFRA',
    'O.S. PERSONAL IND. MADERERA',
    'O.S.D.I.P.P.',
    'O.S.SUPER.IND.METALMECANICA',
    'O.S.T.P.C.H.E.P.Y.A.R.A.',
    'OBSBA',
    'OMINT',
    'OPDEA',
    'OS ASOC DE EMP DE FARMACIA',
    'OSAM',
    'OSDE',
    'OSFATUN',
    'OSMATA',
    'OSME',
    'OSOCNA',
    'OSPE',
    'OSPESUR ( RED OMIP )',
    'OSPIDA',
    'OSPOCE',
    'OSRJA',
    'OSSACRA',
    'CABOTAJE RIOS Y PUERTOS',
    'PODER JUDICIAL',
    'PODER JUDICIAL',
    'PREMEDIC',
    'PREVENCION SALUD',
    'RED ARG.DE SALUD',
    'RED PRESTACIONAL CASA BAYRES',
    'RED PRESTACIONAL PLAN CASA',
    'ROI',
    'SANCOR',
    'SEMPRE',
    'SMAUNSE',
    'SWISS MEDICAL',
]


def qr_patient_create(request):
    """
    Formulario QR público:
    - Crea Patient
    - Guarda adjuntos individuales:
      DNI, CREDENCIAL, ORDEN INTERVENCIÓN, ORDEN MATERIAL (opcional), HC/ESTUDIOS (opcional)
    """
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        dni = request.POST.get('dni', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        coverage = request.POST.get('coverage', '').strip()
        doctor = request.POST.get('doctor', '').strip()
        service = request.POST.get('service', '').strip()
        planned_date_raw = request.POST.get('planned_date')
        external_observations = request.POST.get('external_observations', '').strip()

        planned_date = None
        if planned_date_raw:
            try:
                planned_date = datetime.strptime(planned_date_raw, '%Y-%m-%d').date()
            except ValueError:
                planned_date = None

        patient = Patient.objects.create(
            full_name=full_name,
            dni=dni,
            phone=phone,
            email=email,
            coverage=coverage,
            doctor=doctor,
            service=service,
            planned_date=planned_date,
            external_observations=external_observations,
        )

        file_map = [
            ('dni_file', Attachment.TYPE_DNI),
            ('credencial_file', Attachment.TYPE_CREDENCIAL),
            ('orden_intervencion_file', Attachment.TYPE_ORDEN),
            ('orden_material_file', Attachment.TYPE_MATERIALES),
            ('hc_file', Attachment.TYPE_ESTUDIOS),
        ]

        for field_name, att_type in file_map:
            f = request.FILES.get(field_name)
            if f:
                Attachment.objects.create(
                    patient=patient,
                    file=f,
                    type=att_type,
                )

        return render(request, 'core/patient_form.html', {
            'success': True,
            'tracking_id': patient.tracking_id,
            'services': SERVICIOS_QR,
            'doctors': MEDICOS_QR,
            'coverages': COBERTURAS_QR,
        })

    # GET
    return render(request, 'core/patient_form.html', {
        'services': SERVICIOS_QR,
        'doctors': MEDICOS_QR,
        'coverages': COBERTURAS_QR,
    })


@login_required
def dashboard(request):
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    hace_7_dias = hoy - timedelta(days=7)

    total = Patient.objects.count()
    total_mes = Patient.objects.filter(created_at__date__gte=inicio_mes).count()
    total_semana = Patient.objects.filter(created_at__date__gte=hace_7_dias).count()

    raw_por_estado = (
        Patient.objects.values('status')
        .annotate(c=Count('id'))
        .order_by()
    )
    mapa_estados = {row['status']: row['c'] for row in raw_por_estado}

    status_summary = [
        {"label": "Pendientes", "code": Patient.STATUS_PENDIENTE,
         "count": mapa_estados.get(Patient.STATUS_PENDIENTE, 0)},
        {"label": "Solicitados", "code": Patient.STATUS_SOLICITADO,
         "count": mapa_estados.get(Patient.STATUS_SOLICITADO, 0)},
        {"label": "Autorizados", "code": Patient.STATUS_AUTORIZADO,
         "count": mapa_estados.get(Patient.STATUS_AUTORIZADO, 0)},
        {"label": "Material pendiente", "code": Patient.STATUS_MATERIAL_PENDIENTE,
         "count": mapa_estados.get(Patient.STATUS_MATERIAL_PENDIENTE, 0)},
        {"label": "Rechazos", "code": Patient.STATUS_RECHAZO,
         "count": mapa_estados.get(Patient.STATUS_RECHAZO, 0)},
        {"label": "Reprogramados", "code": Patient.STATUS_REPROGRAMADO,
         "count": mapa_estados.get(Patient.STATUS_REPROGRAMADO, 0)},
    ]

    proximas_hoy = Patient.objects.filter(
        planned_date=hoy
    ).order_by('planned_date', 'service', 'full_name')

    proximas_semana = Patient.objects.filter(
        planned_date__gt=hoy,
        planned_date__lte=hoy + timedelta(days=7)
    ).order_by('planned_date', 'service', 'full_name')

    ultimas = Patient.objects.order_by('-created_at')[:5]

    top_servicios = (
        Patient.objects.values('service')
        .annotate(c=Count('id'))
        .order_by('-c')[:5]
    )
    top_coberturas = (
        Patient.objects.values('coverage')
        .annotate(c=Count('id'))
        .order_by('-c')[:5]
    )

    context = {
        "hoy": hoy,
        "total": total,
        "total_mes": total_mes,
        "total_semana": total_semana,
        "status_summary": status_summary,
        "proximas_hoy": proximas_hoy,
        "proximas_semana": proximas_semana,
        "ultimas": ultimas,
        "top_servicios": top_servicios,
        "top_coberturas": top_coberturas,
    }
    return render(request, "core/dashboard.html", context)


@login_required
def patient_list(request):
    form = PatientFilterForm(request.GET or None)
    qs = Patient.objects.all().order_by('-created_at')

    if form.is_valid():
        q = form.cleaned_data.get('q')
        if q:
            qs = qs.filter(full_name__icontains=q)

        status = form.cleaned_data.get('status')
        if status:
            qs = qs.filter(status=status)

        coverage = form.cleaned_data.get('coverage')
        if coverage:
            qs = qs.filter(coverage=coverage)

        doctor = form.cleaned_data.get('doctor')
        if doctor:
            qs = qs.filter(doctor=doctor)

        service = form.cleaned_data.get('service')
        if service:
            qs = qs.filter(service__icontains=service)

        date_from = form.cleaned_data.get('date_from')
        if date_from:
            qs = qs.filter(planned_date__gte=date_from)

        date_to = form.cleaned_data.get('date_to')
        if date_to:
            qs = qs.filter(planned_date__lte=date_to)

        created_from = form.cleaned_data.get('created_from')
        if created_from:
            qs = qs.filter(created_at__date__gte=created_from)

        created_to = form.cleaned_data.get('created_to')
        if created_to:
            qs = qs.filter(created_at__date__lte=created_to)

    return render(request, 'core/patient_list.html', {
        'patients': qs,
        'form': form,
    })


@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)

    attachment_form = AttachmentForm()
    reprogram_form = ReprogramForm()

    if request.method == "POST":
        if "update_status" in request.POST:
            new_status = request.POST.get("status", patient.status)
            new_obs = request.POST.get("internal_observations", "").strip()

            patient.status = new_status
            patient.internal_observations = new_obs
            patient.save()

            messages.success(request, "Estado y observaciones actualizados.")
            return redirect("core:patient_detail", pk=patient.pk)

        if "add_attachment" in request.POST:
            attachment_form = AttachmentForm(request.POST, request.FILES)
            if attachment_form.is_valid():
                att = attachment_form.save(commit=False)
                att.patient = patient
                att.save()
                messages.success(request, "Archivo agregado correctamente.")
                return redirect("core:patient_detail", pk=patient.pk)

        if "reprogram" in request.POST:
            reprogram_form = ReprogramForm(request.POST, instance=patient)
            if reprogram_form.is_valid():
                reprogram_form.save()
                messages.success(request, "Reprogramación actualizada.")
                return redirect("core:patient_detail", pk=patient.pk)

    context = {
        "patient": patient,
        "attachment_form": attachment_form,
        "reprogram_form": reprogram_form,
    }
    return render(request, "core/patient_detail.html", context)


@login_required
def calendar_view(request):
    return render(request, 'core/calendar.html')


def _service_color(service_name: str) -> str:
    service_name = (service_name or '').lower()
    if 'trauma' in service_name:
        return '#ff5722'
    if 'cardio' in service_name:
        return '#2196f3'
    if 'neuro' in service_name:
        return '#9c27b0'
    return '#4caf50'


@login_required
def calendar_day_view(request):
    """
    Vista que muestra los pacientes programados para un día concreto.
    URL: /calendario/dia/?date=YYYY-MM-DD
    """
    date_str = request.GET.get("date")
    date_obj = parse_date(date_str) if date_str else None

    patients = []
    if date_obj:
        patients = (
            Patient.objects.filter(planned_date=date_obj)
            .order_by("service", "full_name")
        )

    context = {
        "date": date_obj,
        "patients": patients,
    }
    return render(request, "core/calendar_day.html", context)


@login_required
def calendar_events(request):
    events = []
    for p in Patient.objects.all():
        if not p.planned_date:
            continue
        events.append({
            'id': p.id,
            'title': f"{p.full_name} - {p.service}",
            'start': p.planned_date.isoformat(),
            'allDay': True,
            'backgroundColor': _service_color(p.service),
            'borderColor': _service_color(p.service),
        })
    return JsonResponse(events, safe=False)


@login_required
@require_POST
def calendar_move_event(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    new_date_str = request.POST.get('date')
    try:
        new_date = datetime.fromisoformat(new_date_str).date()
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Fecha inválida'}, status=400)
    patient.planned_date = new_date
    patient.last_reprogram_date = timezone.now()
    patient.last_reprogram_reason = "Reprogramado desde calendario"
    patient.status = Patient.STATUS_REPROGRAMADO
    patient.save()
    return JsonResponse({'status': 'ok'})


@login_required
def stats_view(request):
    return render(request, 'core/stats.html')


@login_required
def stats_data(request):
    by_service = list(
        Patient.objects.values('service').annotate(count=Count('id')).order_by('-count')
    )
    by_coverage = list(
        Patient.objects.values('coverage').annotate(count=Count('id')).order_by('-count')[:10]
    )
    by_status = list(
        Patient.objects.values('status').annotate(count=Count('id')).order_by('-count')
    )
    data = {
        'by_service': by_service,
        'by_coverage': by_coverage,
        'by_status': by_status,
    }
    return JsonResponse(data)


@login_required
def export_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pacientes"
    headers = [
        "Tracking ID", "Nombre", "DNI", "Cobertura",
        "Médico", "Servicio", "Fecha intervención", "Estado"
    ]
    ws.append(headers)
    for p in Patient.objects.all():
        ws.append([
            p.tracking_id, p.full_name, p.dni, p.coverage,
            p.doctor, p.service,
            p.planned_date.isoformat() if p.planned_date else "",
            p.get_status_display(),
        ])
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="pacientes.xlsx"'
    return response


@login_required
def export_pdf(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Reporte de Pacientes - Panel OVA")
    y -= 30
    p.setFont("Helvetica", 10)
    for patient in Patient.objects.all()[:100]:
        line = f"{patient.tracking_id} - {patient.full_name} - {patient.coverage} - {patient.get_status_display()}"
        p.drawString(50, y, line)
        y -= 15
        if y < 50:
            p.showPage()
            y = height - 50
    p.showPage()
    p.save()
    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="pacientes.pdf"'
    return response
